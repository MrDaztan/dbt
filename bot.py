import os
import math
import discord
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Inventarios por usuario: {user_id: {"items": {item_name: cantidad}, "coronas": int}}
inventarios = {}

# Tienda dinámica: {nombre: {"emoji": str, "precio": int}}
tienda = {
    "Espada corta": {"emoji": "🗡️", "precio": 25},
    "Escudo de madera": {"emoji": "🛡️", "precio": 30},
    "Poción de curación": {"emoji": "🧪", "precio": 15},
    "Mapa del tesoro": {"emoji": "🗺️", "precio": 40},
    "Cuerda resistente": {"emoji": "🪢", "precio": 12},
    "Antorcha": {"emoji": "🔥", "precio": 10},
    "Anillo misterioso": {"emoji": "💍", "precio": 45},
    "Libro antiguo": {"emoji": "📖", "precio": 20},
    "Moneda de oro": {"emoji": "🪙", "precio": 5},
    "Botella de ron": {"emoji": "🍾", "precio": 18},
}

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command()
async def hola(ctx):
    await ctx.send('¡Hola!')

@bot.command()
async def inventario(ctx):
    user_id = ctx.author.id
    data = inventarios.get(user_id, {"items": {}, "coronas": 0})
    items_inv = data["items"]
    coronas = data["coronas"]

    if not items_inv and coronas == 0:
        await ctx.send("Tu inventario está vacío.")
        return

    msg = f"**Inventario de {ctx.author.display_name}:**\n"
    for item, cantidad in items_inv.items():
        emoji = tienda[item]["emoji"] if item in tienda else ""
        msg += f"{emoji} {item}: {cantidad}\n"
    msg += f"\n💰 Coronas: {coronas}"
    await ctx.send(msg)

@bot.command()
async def coronas(ctx, miembro: discord.Member, cantidad: int):
    user_id = miembro.id
    data = inventarios.setdefault(user_id, {"items": {}, "coronas": 0})
    data["coronas"] += cantidad
    await ctx.send(f"{cantidad} coronas añadidas a {miembro.display_name}. Ahora tiene {data['coronas']} coronas.")

@bot.command()
async def coronasrestar(ctx, miembro: discord.Member, cantidad: int):
    user_id = miembro.id
    data = inventarios.setdefault(user_id, {"items": {}, "coronas": 0})
    data["coronas"] = max(0, data["coronas"] - cantidad)
    await ctx.send(f"{cantidad} coronas restadas a {miembro.display_name}. Ahora tiene {data['coronas']} coronas.")

class TiendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for item_name, data in tienda.items():
            btn = Button(style=discord.ButtonStyle.secondary, emoji=data["emoji"], custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            data = inventarios.setdefault(user_id, {"items": {}, "coronas": 0})
            items_user = data["items"]
            coronas = data["coronas"]
            precio = tienda[item_name]["precio"]

            if item_name not in items_user or items_user[item_name] == 0:
                if coronas >= precio:
                    items_user[item_name] = 1
                    data["coronas"] -= precio
                    await interaction.response.send_message(
                        f"Has **comprado** {item_name} por {precio} coronas. Te quedan {data['coronas']} coronas.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"No tienes suficientes coronas para comprar **{item_name}**. Necesitas {precio}, tienes {coronas}.",
                        ephemeral=True
                    )
            else:
                items_user[item_name] -= 1
                if items_user[item_name] <= 0:
                    del items_user[item_name]
                ganancia = precio // 2
                data["coronas"] += ganancia
                await interaction.response.send_message(
                    f"Has **vendido** {item_name} y recuperado {ganancia} coronas. Ahora tienes {data['coronas']} coronas.",
                    ephemeral=True
                )
        return callback

@bot.command()
async def tienda(ctx):
    if not tienda:
        await ctx.send("La tienda está vacía.")
        return

    msg = "**🏪 Tienda de objetos mágicos**\n\n"
    for item_name, data in tienda.items():
        msg += f"{data['emoji']} {item_name} - {data['precio']} coronas\n"

    view = TiendaView()
    await ctx.send(msg, view=view)

@bot.command()
async def editaritem(ctx, accion: str, nombre: str, emoji: str = None, precio: int = None):
    if accion.lower() == "agregar":
        if not emoji or precio is None:
            await ctx.send("Debes especificar un emoji y un precio para agregar.")
            return
        tienda[nombre] = {"emoji": emoji, "precio": precio}
        await ctx.send(f"✅ {nombre} agregado a la tienda por {precio} coronas.")
    elif accion.lower() == "quitar":
        if nombre in tienda:
            del tienda[nombre]
            await ctx.send(f"🗑️ {nombre} ha sido removido de la tienda.")
        else:
            await ctx.send(f"❌ {nombre} no está en la tienda.")
    else:
        await ctx.send("Usa `agregar` o `quitar` como primer argumento.")
