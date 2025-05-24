import os
import discord
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario inventarios: {user_id: {item_name: cantidad}}
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

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command()
async def hola(ctx):
    await ctx.send('¡Hola!')

@bot.command()
async def inventario(ctx):
    user_id = ctx.author.id
    inv = inventarios.get(user_id, {})
    if not inv:
        await ctx.send("Tu inventario está vacío.")
        return
    
    msg = f"**Inventario de {ctx.author.display_name}:**\n"
    for item, cantidad in inv.items():
        msg += f"{items_dict[item]} {item}: {cantidad}\n"
    await ctx.send(msg)

# Crear un diccionario para obtener emoji por nombre de item rápido
items_dict = {item: emoji for item, emoji in items}

class EventoView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Sin timeout para mantener los botones activos

        # Crear un botón por cada item con su emoji
        for item_name, emoji in items:
            # Usamos el label vacío para mostrar solo el emoji
            btn = Button(style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=item_name)
            btn.callback = self.make_callback(item_name)
            self.add_item(btn)

    def make_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            inv = inventarios.setdefault(user_id, {})

            if item_name not in inv or inv[item_name] == 0:
                inv[item_name] = 1
                accion = "añadido"
            else:
                # Si ya tiene el item, al hacer click lo restamos
                inv[item_name] -= 1
                if inv[item_name] <= 0:
                    del inv[item_name]
                accion = "restado"

            await interaction.response.send_message(
                f"Has {accion} **{item_name}** a tu inventario. Ahora tienes: {inv.get(item_name, 0)}.", 
                ephemeral=True  # Mensaje solo visible para quien clickeó
            )
        return callback

@bot.command()
async def evento(ctx):
    # Construir mensaje con lista de ítems y emojis
    msg = "**¡Evento! Estos son los objetos disponibles:**\n"
    for item_name, emoji in items:
        msg += f"{emoji} - {item_name}\n"

    view = EventoView()
    await ctx.send(msg, view=view)


bot.run(os.getenv("DISCORD_TOKEN"))
