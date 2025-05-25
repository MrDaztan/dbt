import os
import json
import discord
from discord.ext import commands
from discord.ui import Button, View

# Configura ruta persistente (Render Disk debe montarse en /data)
INVENTARIO_PATH = "inventarios.json"
TIENDA_PATH = "tienda.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionarios de memoria
inventarios = {}
tienda_data = {}

# Cargar desde disco
def cargar_datos():
    global inventarios, tienda_data
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

def guardar_inventarios():
    with open(INVENTARIO_PATH, "w", encoding="utf-8") as f:
        json.dump(inventarios, f, indent=2, ensure_ascii=False)

def guardar_tienda():
    with open(TIENDA_PATH, "w", encoding="utf-8") as f:
        json.dump(tienda_data, f, indent=2, ensure_ascii=False)

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
    msg += f"👑 Coronas: {inv.get('coronas', 0)}\n"
    for item, cantidad in inv.items():
        if item != "coronas":
            emoji = tienda_data.get(item, {}).get("emoji", "")
            msg += f"{emoji} {item}: {cantidad}\n"
    await ctx.send(msg)

@bot.command()
async def coronas(ctx, cantidad: int, miembro: discord.Member = None):
    if miembro is None:
        miembro = ctx.author
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv["coronas"] = inv.get("coronas", 0) + cantidad
    guardar_inventarios()
    await ctx.send(f"{miembro.display_name} ha recibido 👑 {cantidad} coronas. Total: {inv['coronas']}")

@bot.command(name="coronas-")
async def coronas_restar(ctx, cantidad: int, miembro: discord.Member = None):
    if miembro is None:
        miembro = ctx.author
    user_id = str(miembro.id)
    inv = inventarios.setdefault(user_id, {"coronas": 0})
    inv["coronas"] = max(0, inv.get("coronas", 0) - cantidad)
    guardar_inventarios()
    await ctx.send(f"A {miembro.display_name} se le han restado 👑 {cantidad} coronas. Total: {inv['coronas']}")

class TiendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for item_name, data in tienda_data.items():
            emoji = data.get("emoji", "❔")
            btn = Button(style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            inv = inventarios.setdefault(user_id, {"coronas": 0})
            precio = tienda_data[item_name]["precio"]

            if item_name not in inv:
                if inv["coronas"] >= precio:
                    inv[item_name] = 1
                    inv["coronas"] -= precio
                    await interaction.response.send_message(
                        f"Compraste {item_name} por 👑 {precio}. Te quedan: {inv['coronas']}", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ No tienes suficientes coronas.", ephemeral=True)
            else:
                venta = precio // 2
                inv[item_name] -= 1
                if inv[item_name] <= 0:
                    del inv[item_name]
                inv["coronas"] += venta
                await interaction.response.send_message(
                    f"Vendiste {item_name} por 👑 {venta}. Ahora tienes: {inv['coronas']}", ephemeral=True)

            guardar_inventarios()
        return callback

@bot.command()
async def tienda(ctx):
    if not tienda:
        await ctx.send("La tienda está vacía.")
        return

    msg = "**🏪 Tienda de objetos:**\n"
    for nombre, data in tienda_data.items():
        msg += f"{data['emoji']} {nombre} — 👑 {data['precio']} coronas\n"

    view = TiendaView()
    await ctx.send(msg, view=view)

@bot.command()
async def editaritem(ctx, accion: str, nombre: str, emoji: str = None, precio: int = None):
    if accion.lower() == "agregar" and emoji and precio is not None:
        tienda_data[nombre] = {"emoji": emoji, "precio": precio}
        guardar_tienda()
        await ctx.send(f"✅ Añadido: {emoji} {nombre} — 👑 {precio}")
    elif accion.lower() == "quitar":
        if nombre in tienda_data:
            del tienda[nombre]
            guardar_tienda()
            await ctx.send(f"❌ Eliminado {nombre} de la tienda.")
        else:
            await ctx.send("Ese item no está en la tienda.")
    else:
        await ctx.send("Uso: `!editaritem agregar nombre emoji precio` o `!editaritem quitar nombre`")

# Cargar datos antes de ejecutar el bot
cargar_datos()

# Ejecuta el bot con token desde variable de entorno
bot.run(os.getenv("DISCORD_TOKEN"))
