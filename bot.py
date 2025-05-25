import os
import json
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import TextStyle

INVENTARIO_PATH = "inventarios.json"
TIENDA_PATH = "tienda.json"
STATS_PATH = "stats.json"
RECETAS_PATH = "recetas.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

inventarios = {}
tienda_data = {}
stats_data = {}
recetas_data = {}

# Cargar desde disco
def cargar_datos():
    global inventarios, tienda_data, stats_data, recetas_data
    try:
        with open(RECETAS_PATH, "r", encoding="utf-8") as f:
            recetas_data.update(json.load(f))
    except FileNotFoundError:
        pass
    try:
        with open(INVENTARIO_PATH, "r", encoding="utf-8") as f:
            inventarios.update(json.load(f))
    except FileNotFoundError:
        pass

    try:
        with open(TIENDA_PATH, "r", encoding="utf-8") as f:
            tienda_data.update(json.load(f))
    except FileNotFoundError:
        pass

    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            stats_data.update(json.load(f))
    except FileNotFoundError:
        pass

def guardar_inventarios():
    with open(INVENTARIO_PATH, "w", encoding="utf-8") as f:
        json.dump(inventarios, f, indent=2, ensure_ascii=False)

def guardar_tienda():
    with open(TIENDA_PATH, "w", encoding="utf-8") as f:
        json.dump(tienda_data, f, indent=2, ensure_ascii=False)

def guardar_stats():
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

def es_master(ctx):
    return any(r.name.lower() == "master" for r in ctx.author.roles)

@bot.command()
async def hola(ctx):
    await ctx.send('¡Hola!')

@bot.command()
async def inventario(ctx):
    user_id = str(ctx.author.id)
    inv = inventarios.get(user_id, {"coronas": 0})
    msg = f"**Inventario de {ctx.author.display_name}:**\n"
    msg += f"🪙 Coronas: {inv.get('coronas', 0)}\n"
    for item, cantidad in inv.items():
        if item != "coronas":
            emoji = tienda_data.get(item, {}).get("emoji", "")
            msg += f"{emoji} {item}: {cantidad}\n"
    await ctx.send(msg)

@bot.command()
async def comandos(ctx):
    master = es_master(ctx)
    msg = "**Lista de comandos:**\n"
    msg += "`!inventario` - Muestra tu inventario actual.\n"
    msg += "`!tienda` - Muestra los objetos disponibles en la tienda.\n"
    msg += "`!stats` - Muestra tus estadísticas de personaje.\n"
    if master:
        msg += "`!coronas <cantidad> [@usuario]` - Da coronas a un jugador (solo master).\n"
        msg += "`!coronas- <cantidad> [@usuario]` - Resta coronas a un jugador (solo master).\n"
        msg += "`!editaritem agregar <nombre> <emoji> <precio>` - Añade un item a la tienda (solo master).\n"
        msg += "`!editaritem quitar <nombre>` - Quita un item de la tienda (solo master).\n"
        msg += "`!daritem <usuario> <nombre_item> <cantidad>` - Da un item directo a un jugador (solo master).\n"
    await ctx.send(msg)

@bot.command()
async def coronas(ctx, cantidad: int, miembro: discord.Member = None):
    if not es_master(ctx):
        await ctx.send("❌ Solo los usuarios con el rol 'master' pueden usar este comando.")
        return
    if miembro is None:
        miembro = ctx.author
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv["coronas"] = inv.get("coronas", 0) + cantidad
    guardar_inventarios()
    await ctx.send(f"{miembro.display_name} ha recibido 🪙 {cantidad} coronas. Total: {inv['coronas']}")

@bot.command(name="coronas-")
async def coronas_restar(ctx, cantidad: int, miembro: discord.Member = None):
    if not es_master(ctx):
        await ctx.send("❌ Solo los usuarios con el rol 'master' pueden usar este comando.")
        return
    if miembro is None:
        miembro = ctx.author
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv["coronas"] = max(0, inv.get("coronas", 0) - cantidad)
    guardar_inventarios()
    await ctx.send(f"A {miembro.display_name} se le han restado 🪙 {cantidad} coronas. Total: {inv['coronas']}")

@bot.command()
async def daritem(ctx, miembro: discord.Member, nombre: str, cantidad: int):
    if not es_master(ctx):
        await ctx.send("❌ Solo los usuarios con el rol 'master' pueden usar este comando.")
        return
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv[nombre] = inv.get(nombre, 0) + cantidad
    guardar_inventarios()
    await ctx.send(f"✅ Se le ha dado {cantidad}x {nombre} a {miembro.display_name}.")

class TiendaView(View):
    def __init__(self, modo, autor):
        super().__init__(timeout=None)
        self.modo = modo  # 'comprar' o 'vender'
        self.autor = autor
        self.transacciones = []

        for item_name, data in tienda_data.items():
            emoji = data.get("emoji", "❔")
            btn = Button(style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.autor:
                await interaction.response.send_message("❌ Esta tienda no es para ti.", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            inv = inventarios.setdefault(user_id, {"coronas": 0})
            precio = tienda_data[item_name]["precio"]

            if self.modo == "comprar":
                if inv["coronas"] >= precio:
                    inv[item_name] = inv.get(item_name, 0) + 1
                    inv["coronas"] -= precio
                    self.transacciones.append(f"🛒 {interaction.user.display_name} compró {item_name} por 🪙 {precio}")
                    await interaction.response.send_message(f"Compraste {item_name} por 🪙 {precio}. Te quedan: {inv['coronas']}", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No tienes suficientes coronas.", ephemeral=True)
            else:
                if inv.get(item_name, 0) > 0:
                    venta = precio // 2
                    inv[item_name] -= 1
                    if inv[item_name] <= 0:
                        del inv[item_name]
                    inv["coronas"] += venta
                    self.transacciones.append(f"💰 {interaction.user.display_name} vendió {item_name} por 🪙 {venta}")
                    await interaction.response.send_message(f"Vendiste {item_name} por 🪙 {venta}. Ahora tienes: {inv['coronas']}", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No tienes ese objeto para vender.", ephemeral=True)

            guardar_inventarios()

            if len(self.transacciones) >= 1:
                canal_log = discord.utils.get(interaction.guild.text_channels, name="tienda-log")
                if canal_log:
                    for trans in self.transacciones:
                        await canal_log.send(trans)
                    self.transacciones.clear()

        return callback

@bot.command()
async def tienda(ctx):
    if not tienda_data:
        await ctx.send("La tienda está vacía.")
        return

    opciones = Select(
        placeholder="¿Qué deseas hacer?",
        options=[
            discord.SelectOption(label="Comprar", value="comprar", emoji="🛒"),
            discord.SelectOption(label="Vender", value="vender", emoji="💰")
        ]
    )

    async def select_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            await interaction.response.send_message("❌ Esta tienda no es para ti.", ephemeral=True)
            return

        modo = opciones.values[0]
        view = TiendaView(modo, ctx.author)
        msg = "**Tienda de objetos:**\n"
        for nombre, data in tienda_data.items():
            msg += f"{data['emoji']} {nombre} — 🪙 {data['precio']} coronas\n"
        await interaction.response.send_message(msg, view=view, ephemeral=True)

    opciones.callback = select_callback
    view = View()
    view.add_item(opciones)
    await ctx.send("¿Qué deseas hacer en la tienda?", view=view, ephemeral=True)

@bot.command()
async def editaritem(ctx, accion: str, nombre: str, emoji: str = None, precio: int = None):
    if not es_master(ctx):
        await ctx.send("❌ Solo los usuarios con el rol 'master' pueden usar este comando.")
        return

    if accion.lower() == "agregar" and emoji and precio is not None:
        tienda_data[nombre] = {"emoji": emoji, "precio": precio}
        guardar_tienda()
        await ctx.send(f"✅ Añadido: {emoji} {nombre} — 🪙 {precio}")
    elif accion.lower() == "quitar":
        if nombre in tienda_data:
            del tienda_data[nombre]
            guardar_tienda()
            await ctx.send(f"❌ Eliminado {nombre} de la tienda.")
        else:
            await ctx.send("Ese item no está en la tienda.")
    else:
        await ctx.send("Uso: `!editaritem agregar <nombre> <emoji> <precio>` o `!editaritem quitar <nombre>`")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    roles = [r.name.lower() for r in ctx.author.roles]
    raza = "humano"
    if "elfo" in roles:
        raza = "elfo"
    elif "enano" in roles:
        raza = "enano"

    stats = stats_data.setdefault(user_id, {"clase": "", "salud": 100, "mana": 50})
    stats_data[user_id]["raza"] = raza
    guardar_stats()

    embed = discord.Embed(title=f"🧙 Stats de {ctx.author.display_name}", color=discord.Color.purple())
    embed.add_field(name="🧬 Raza", value=f"`{raza.title()}`", inline=True)
    embed.add_field(name="🛡️ Clase", value=f"`{stats.get('clase', '')}`", inline=True)
    embed.add_field(name="❤️ Salud", value=f"`{stats.get('salud', 0)}`", inline=True)
    embed.add_field(name="💧 Maná", value=f"`{stats.get('mana', 0)}`", inline=True)
    await ctx.send(embed=embed)

class CategoriaForja(View):
    def __init__(self, autor):
        super().__init__(timeout=None)
        self.autor = autor
        self.select = Select(
            placeholder="Elige una categoría",
            options=[
                discord.SelectOption(label="Armas", value="armas", emoji="⚔️"),
                discord.SelectOption(label="Armaduras", value="armaduras", emoji="🛡️"),
                discord.SelectOption(label="Accesorios", value="accesorios", emoji="💍")
            ]
        )
        self.select.callback = self.categoria_callback
        self.add_item(self.select)

    async def categoria_callback(self, interaction: discord.Interaction):
        if interaction.user != self.autor:
            await interaction.response.send_message("❌ Este menú no es para ti.", ephemeral=True)
            return

        categoria = self.select.values[0]
        view = ItemsForjaView(categoria, self.autor)
        await interaction.response.send_message(f"**Selecciona un objeto de `{categoria.title()}`:**", view=view, ephemeral=True)

class ItemsForjaView(View):
    def __init__(self, categoria, autor):
        super().__init__(timeout=None)
        self.autor = autor
        self.categoria = categoria
        opciones = [
            discord.SelectOption(label=item, value=item, emoji=data.get("emoji", "❔"))
            for item, data in recetas_data[categoria].items()
        ]
        self.select = Select(placeholder="Elige un objeto", options=opciones)
        self.select.callback = self.item_callback
        self.add_item(self.select)

    async def item_callback(self, interaction: discord.Interaction):
        if interaction.user != self.autor:
            await interaction.response.send_message("❌ Este menú no es para ti.", ephemeral=True)
            return

        item = self.select.values[0]
        receta = recetas_data[self.categoria][item]["recursos"]
        recursos_str = "\n".join([f"- {nombre}: {cantidad}" for nombre, cantidad in receta.items()])
        emoji = recetas_data[self.categoria][item].get("emoji", "❔")

        boton = Button(label=f"Fabricar {item}", emoji=emoji, style=discord.ButtonStyle.green)

        async def fabricar_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user != self.autor:
                await btn_interaction.response.send_message("❌ Este botón no es para ti.", ephemeral=True)
                return

            user_id = str(self.autor.id)
            inv = inventarios.setdefault(user_id, {"coronas": 0})

            if all(inv.get(recurso, 0) >= cantidad for recurso, cantidad in receta.items()):
                for recurso, cantidad in receta.items():
                    inv[recurso] -= cantidad
                    if inv[recurso] <= 0:
                        del inv[recurso]
                inv[item] = inv.get(item, 0) + 1
                guardar_inventarios()
                await btn_interaction.response.send_message(f"✅ ¡Fabricaste {emoji} {item} con éxito!", ephemeral=True)
            else:
                await btn_interaction.response.send_message("❌ No tienes los recursos necesarios para fabricar este objeto.", ephemeral=True)

        boton.callback = fabricar_callback
        view = View()
        view.add_item(boton)

        await interaction.response.send_message(
            f"**{emoji} {item}** requiere:\n{recursos_str}",
            view=view,
            ephemeral=True
        )

@bot.command()
async def forja(ctx):
    view = CategoriaForja(ctx.author)
    await ctx.send("🔨 Bienvenido a la **Forja**. Elige una categoría:", view=view, ephemeral=True)


cargar_datos()
bot.run(os.getenv("DISCORD_TOKEN"))
