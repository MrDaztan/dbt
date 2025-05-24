import os
import random
import discord
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario inventarios: {user_id: {"items": {item_name: cantidad}, "coronas": cantidad}}
inventarios = {}

# Items y emojis del evento (puedes cambiar)
items = [
    ("Espada corta", "🗡️"),
    ("Escudo de madera", "🛡️"),
    ("Poción de curación", "🧪"),
    ("Mapa del tesoro", "🗺️"),
    ("Cuerda resistente", "🪢"),
    ("Antorcha", "🔥"),
    ("Anillo misterioso", "💍"),
    ("Libro antiguo", "📖"),
    ("Moneda de oro", "🪙"),
    ("Botella de ron", "🍾"),
]

# Precios aleatorios al cargar el bot
precios = {item: random.randint(1, 50) for item, _ in items}
items_dict = {item: emoji for item, emoji in items}

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
        msg += f"{items_dict[item]} {item}: {cantidad}\n"
    msg += f"\n💰 Coronas: {coronas}"
    await ctx.send(msg)

@bot.command()
async def coronas(ctx, miembro: discord.Member, cantidad: int):
    user_id = miembro.id
    data = inventarios.setdefault(user_id, {"items": {}, "coronas": 0})
    data["coronas"] += cantidad
    await ctx.send(f"{cantidad} coronas añadidas a {miembro.display_name}. Ahora tiene {data['coronas']} coronas.")

class TiendaView(View):
    def __init__(self):
        super().__init__(timeout=None)

        for item_name, emoji in items:
            btn = Button(style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            data = inventarios.setdefault(user_id, {"items": {}, "coronas": 0})
            items_user = data["items"]
            coronas = data["coronas"]
            precio = precios[item_name]

            if item_name not in items_user or items_user[item_name] == 0:
                # Comprar
                if coronas >= precio:
                    items_user[item_name] = 1
                    data["coronas"] -= precio
                    accion = "comprado"
                    await interaction.response.send_message(
                        f"Has **{accion}** {item_name} por {precio} coronas. Te quedan {data['coronas']} coronas.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"No tienes suficientes coronas para comprar **{item_name}**. Necesitas {precio}, tienes {coronas}.",
                        ephemeral=True
                    )
            else:
                # Vender
                items_user[item_name] -= 1
                if items_user[item_name] <= 0:
                    del items_user[item_name]
                data["coronas"] += precio
                await interaction.response.send_message(
                    f"Has **vendido** {item_name} y recuperado {precio} coronas. Ahora tienes {data['coronas']} coronas.",
                    ephemeral=True
                )

        return callback

@bot.command()
async def tienda(ctx):
    msg = "**🏪 Tienda de objetos mágicos**\n\n"
    for item_name, emoji in items:
        precio = precios[item_name]
        msg += f"{emoji} {item_name} - {precio} coronas\n"

    view = TiendaView()
    await ctx.send(msg, view=view)

bot.run(os.getenv("DISCORD_TOKEN"))
