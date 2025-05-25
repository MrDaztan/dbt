import os
import json
import discord
from discord.ext import commands
from discord.ui import Button, View, Select

INVENTARIO_PATH = "inventarios.json"
TIENDA_PATH = "tienda.json"
STATS_PATH = "stats.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

inventarios = {}
tienda_data = {}
stats_data = {}

# Cargar desde disco
def cargar_datos():
    global inventarios, tienda_data, stats_data
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
    msg = (
        "**Lista de comandos:**\n"
        "`!inventario` - Muestra tu inventario actual.\n"
        "`!tienda` - Interactúa con la tienda.\n"
        "`!stats` - Muestra tus estadísticas de personaje.\n"
        "`!coronas <cantidad> [@usuario]` - Da coronas a un jugador (solo master).\n"
        "`!coronas- <cantidad> [@usuario]` - Resta coronas a un jugador (solo master).\n"
        "`!editaritem agregar <nombre> <emoji> <precio>` - Añade un item a la tienda (solo master).\n"
        "`!editaritem quitar <nombre>` - Quita un item de la tienda (solo master).\n"
        "`!daritem <usuario> <nombre_item> <cantidad>` - Da un item directo a un jugador (solo master).\n"
    )
    await ctx.send(msg)

def es_master(ctx):
    return any(r.name.lower() == "master" for r in ctx.author.roles)

@bot.command()
async def coronas(ctx, cantidad: int, miembro: discord.Member = None):
    if not es_master(ctx):
        await ctx.send("❌ Solo los usuarios con el rol 'master' pueden usar este comando.")
        return
    if miembro is None:
        miembro = ctx.author
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv["coronas"] += cantidad
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
    inv["coronas"] = max(0, inv["coronas"] - cantidad)
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
    def __init__(self, accion, autor):
        super().__init__(timeout=30)
        self.accion = accion
        self.autor = autor
        self.transacciones = []
        for item_name, data in tienda_data.items():
            emoji = data.get("emoji", "❔")
            btn = Button(style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.autor.id:
                await interaction.response.send_message("❌ Esta tienda no es para ti.", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            inv = inventarios.setdefault(user_id, {"coronas": 0})
            precio = tienda_data[item_name]["precio"]

            if self.accion == "comprar":
                if inv["coronas"] >= precio:
                    inv[item_name] = inv.get(item_name, 0) + 1
                    inv["coronas"] -= precio
                    self.transacciones.append(f"✅ {interaction.user.display_name} compró {item_name} por 🪙 {precio}.")
                    await interaction.response.send_message(f"Compraste {item_name} por 🪙 {precio}. Te quedan: {inv['coronas']}", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No tienes suficientes coronas.", ephemeral=True)

            elif self.accion == "vender":
                if inv.get(item_name, 0) > 0:
                    inv[item_name] -= 1
                    if inv[item_name] <= 0:
                        del inv[item_name]
                    venta = precio // 2
                    inv["coronas"] += venta
                    self.transacciones.append(f"🔻 {interaction.user.display_name} vendió {item_name} por 🪙 {venta}.")
                    await interaction.response.send_message(f"Vendiste {item_name} por 🪙 {venta}. Ahora tienes: {inv['coronas']}", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No tienes ese objeto para vender.", ephemeral=True)

            guardar_inventarios()
        return callback

@bot.command()
async def tienda(ctx):
    if not tienda_data:
        await ctx.send("La tienda está vacía.")
        return

    options = [
        discord.SelectOption(label="Comprar", value="comprar", emoji="🛒"),
        discord.SelectOption(label="Vender", value="vender", emoji="💰")
    ]

    select = Select(placeholder="¿Qué deseas hacer?", options=options)

    async def select_callback(interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ Solo la persona que usó el comando puede elegir.", ephemeral=True)
            return

        accion = select.values[0]
        view = TiendaView(accion, ctx.author)

        msg = f"**🏪 Tienda - Modo {accion.capitalize()}**\n"
        for nombre, data in tienda_data.items():
            msg += f"{data['emoji']} {nombre} — 🪙 {data['precio']} coronas\n"

        await interaction.response.send_message(msg, view=view, ephemeral=True)
        await ctx.send(f"📝 {ctx.author.display_name} abrió la tienda en modo {accion}.")

    select.callback = select_callback
    view = View()
    view.add_item(select)

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

    razas_validas = {"humano": "Humano", "enano": "Enano", "elfo": "Elfo"}
    razas_encontradas = [razas_validas[r] for r in razas_validas if r in roles]

    if not razas_encontradas:
        raza = "Humano"
    elif len(razas_encontradas) == 1:
        raza = razas_encontradas[0]
    elif len(razas_encontradas) == 2:
        raza = f"Medio {razas_encontradas[1]}"
    else:
        raza = " y ".join(razas_encontradas)

    stats = stats_data.get(user_id, {
        "clase": "Aventurero",
        "salud": 100,
        "mana": 50
    })
    stats["raza"] = raza
    stats_data[user_id] = stats
    guardar_stats()

    embed = discord.Embed(title=f"📜 Stats de {ctx.author.display_name}", color=0x1abc9c)
    embed.add_field(name="🧬 Raza", value=stats["raza"], inline=True)
    embed.add_field(name="⚔️ Clase", value=stats["clase"], inline=True)
    embed.add_field(name="❤️ Salud", value=f"{stats['salud']}", inline=True)
    embed.add_field(name="🔮 Mana", value=f"{stats['mana']}", inline=True)
    await ctx.send(embed=embed)

cargar_datos()
bot.run(os.getenv("DISCORD_TOKEN"))
