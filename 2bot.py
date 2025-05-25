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

def cargar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

inventarios = cargar_json(INVENTARIO_PATH)
tienda_data = cargar_json(TIENDA_PATH)
stats_data = cargar_json(STATS_PATH)
recetas_data = cargar_json(RECETAS_PATH)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

def es_master(ctx):
    return any(r.name.lower() == "master" for r in ctx.author.roles)

@bot.command()
async def comandos(ctx):
    master = es_master(ctx)
    msg = "**Lista de comandos:**\n"
    msg += "`!inventario` - Muestra tu inventario.\n"
    msg += "`!tienda` - Accede a la tienda para comprar o vender.\n"
    msg += "`!stats` - Muestra tus estadísticas.\n"
    msg += "`!forja` - Abre el sistema de forja para fabricar objetos.\n"
    if master:
        msg += "`!coronas <cantidad> [@usuario]` - Da coronas.\n"
        msg += "`!coronas- <cantidad> [@usuario]` - Resta coronas.\n"
        msg += "`!editaritem agregar <nombre> <emoji> <precio>` - Agrega item a tienda.\n"
        msg += "`!editaritem quitar <nombre>` - Quita item de tienda.\n"
        msg += "`!daritem <usuario> <item> <cantidad>` - Da items.\n"
        msg += "`!quitaritem <usuario> <item> <cantidad>` - Quita items.\n"
        msg += "`!cambiarsalud <usuario> <cantidad>` - Cambia salud máxima y actual.\n"
        msg += "`!cambiarmana <usuario> <cantidad>` - Cambia maná máximo y actual.\n"
    await ctx.send(msg)

@bot.command()
async def inventario(ctx):
    user_id = str(ctx.author.id)
    inv = inventarios.get(user_id, {"coronas": 0})

    msg = f"**Inventario de {ctx.author.display_name}:**\n"
    msg += f"🪙 Coronas: {inv.get('coronas', 0)}\n"

    for item, cant in inv.items():
        if item != "coronas":
            emoji = tienda_data.get(item, {}).get("emoji", "❔")
            msg += f"{emoji} {item}: {cant}\n"

    await ctx.send(msg)

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
    guardar_json(stats_data, STATS_PATH)

    salud_base = stats.get("salud", 0)
    mana_base = stats.get("mana", 0)
    salud_total = salud_base
    mana_total = mana_base

    inv = inventarios.get(user_id, {})
    for item, cant in inv.items():
        if item != "coronas":
            efecto = tienda_data.get(item, {}).get("stats", {})
            salud_total += efecto.get("salud", 0) * cant
            mana_total += efecto.get("mana", 0) * cant

    embed = discord.Embed(title=f"🧙 Stats de {ctx.author.display_name}", color=discord.Color.purple())
    embed.add_field(name="Salud", value=f"`Base: {salud_base} + Bonus: {salud_total - salud_base} = {salud_total}`", inline=False)
    embed.add_field(name="Maná", value=f"`Base: {mana_base} + Bonus: {mana_total - mana_base} = {mana_total}`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def coronas(ctx, cantidad: int, miembro: discord.Member = None):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    miembro = miembro or ctx.author
    uid = str(miembro.id)
    inventarios.setdefault(uid, {"coronas": 0})
    inventarios[uid]["coronas"] += cantidad
    guardar_json(inventarios, INVENTARIO_PATH)
    await ctx.send(f"✅ {miembro.display_name} recibió {cantidad} coronas.")

@bot.command(name="coronas-")
async def restar_coronas(ctx, cantidad: int, miembro: discord.Member = None):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    miembro = miembro or ctx.author
    uid = str(miembro.id)
    inventarios.setdefault(uid, {"coronas": 0})
    inventarios[uid]["coronas"] = max(0, inventarios[uid]["coronas"] - cantidad)
    guardar_json(inventarios, INVENTARIO_PATH)
    await ctx.send(f"❌ Se restaron {cantidad} coronas a {miembro.display_name}.")

@bot.command()
async def daritem(ctx, miembro: discord.Member, nombre: str, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    inv = inventarios.setdefault(uid, {"coronas": 0})
    inv[nombre] = inv.get(nombre, 0) + cantidad
    guardar_json(inventarios, INVENTARIO_PATH)
    await ctx.send(f"✅ {miembro.display_name} recibió {cantidad}x {nombre}.")

@bot.command()
async def quitaritem(ctx, miembro: discord.Member, nombre: str, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    inv = inventarios.setdefault(uid, {"coronas": 0})
    if nombre in inv:
        inv[nombre] = max(0, inv[nombre] - cantidad)
        if inv[nombre] == 0:
            del inv[nombre]
        guardar_json(inventarios, INVENTARIO_PATH)
        await ctx.send(f"❌ Se quitaron {cantidad}x {nombre} a {miembro.display_name}.")
    else:
        await ctx.send(f"{miembro.display_name} no tiene {nombre}.")

@bot.command()
async def cambiarsalud(ctx, miembro: discord.Member, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    stats_data.setdefault(uid, {})
    stats_data[uid]["salud"] = cantidad
    guardar_json(stats_data, STATS_PATH)
    await ctx.send(f"💖 Salud de {miembro.display_name} actualizada a {cantidad}.")

@bot.command()
async def cambiarmana(ctx, miembro: discord.Member, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    stats_data.setdefault(uid, {})
    stats_data[uid]["mana"] = cantidad
    guardar_json(stats_data, STATS_PATH)
    await ctx.send(f"🔮 Maná de {miembro.display_name} actualizado a {cantidad}.")

@bot.command()
async def tienda(ctx):
    if not tienda_data:
        return await ctx.send("La tienda está vacía.")
    opciones = Select(placeholder="¿Comprar o vender?", options=[
        discord.SelectOption(label="Comprar", value="comprar", emoji="🛒"),
        discord.SelectOption(label="Vender", value="vender", emoji="💰")
    ])

    async def select_callback(interaction):
        if interaction.user != ctx.author:
            return await interaction.response.send_message("No es tu tienda.", ephemeral=True)
        modo = opciones.values[0]
        view = View()

        for nombre, data in tienda_data.items():
            btn = Button(label=nombre, emoji=data["emoji"], style=discord.ButtonStyle.secondary)

            async def item_callback(i, nombre=nombre):
                uid = str(i.user.id)
                inv = inventarios.setdefault(uid, {"coronas": 0})
                precio = tienda_data[nombre]["precio"]
                stats = tienda_data[nombre].get("stats", {})

                if modo == "comprar":
                    if inv["coronas"] >= precio:
                        inv[nombre] = inv.get(nombre, 0) + 1
                        inv["coronas"] -= precio
                        for stat, value in stats.items():
                            stats_data.setdefault(uid, {}).setdefault(stat, 0)
                            stats_data[uid][stat] += value
                        guardar_json(inventarios, INVENTARIO_PATH)
                        guardar_json(stats_data, STATS_PATH)

                        if "pocion" in nombre.lower():
                            if "salud" in nombre.lower():
                                stats_data[uid]["salud_actual"] = min(
                                    stats_data[uid].get("salud_actual", 100) + 10,
                                    stats_data[uid].get("salud_max", 100))
                            elif "mana" in nombre.lower():
                                stats_data[uid]["mana_actual"] = min(
                                    stats_data[uid].get("mana_actual", 50) + 10,
                                    stats_data[uid].get("mana_max", 50))
                            inv[nombre] -= 1
                            await i.response.send_message(f"Usaste {nombre} y restauraste 10 puntos.", ephemeral=True)
                        else:
                            await i.response.send_message(f"Compraste {nombre} por {precio} coronas.", ephemeral=True)

                        await log_event(TIENDA_LOG_CHANNEL, f"{ctx.author.display_name} compró {nombre} por {precio} 🪙")
                    else:
                        await i.response.send_message("No tienes suficientes coronas.", ephemeral=True)

                else:  # Vender
                    if inv.get(nombre, 0) > 0:
                        inv[nombre] -= 1
                        inv["coronas"] += precio // 2
                        for stat, value in stats.items():
                            stats_data[uid][stat] = stats_data[uid].get(stat, 0) - value
                        guardar_json(inventarios, INVENTARIO_PATH)
                        guardar_json(stats_data, STATS_PATH)
                        await i.response.send_message(f"Vendiste {nombre} por {precio // 2} coronas.", ephemeral=True)

                        await log_event(TIENDA_LOG_CHANNEL, f"{ctx.author.display_name} vendió {nombre} por {precio // 2} 🪙")
                    else:
                        await i.response.send_message("No tienes ese objeto.", ephemeral=True)

            btn.callback = item_callback
            view.add_item(btn)

        await interaction.response.send_message(f"Modo: {modo}", view=view, ephemeral=True)

    opciones.callback = select_callback
    view = View()
    view.add_item(opciones)
    await ctx.send("Selecciona una opción:", view=view)

@bot.command()
async def forja(ctx):
    if not recetas_data:
        return await ctx.send("⚒️ No hay recetas cargadas.")
    await ctx.send("⚒️ Bienvenido a la forja:", view=view(ctx.author))

@bot.command()
async def daritem(ctx, miembro: discord.Member, cantidad: int, *, nombre: str):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")

    uid = str(miembro.id)
    inv = inventarios.setdefault(uid, {"coronas": 0})
    inv[nombre] = inv.get(nombre, 0) + cantidad
    guardar_json(inventarios, INVENTARIO_PATH)

    await ctx.send(f"✅ {miembro.display_name} recibió {cantidad}x {nombre}.")

@bot.command()
async def quitaritem(ctx, miembro: discord.Member, nombre: str, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    inv = inventarios.setdefault(uid, {"coronas": 0})
    if inv.get(nombre, 0) >= cantidad:
        inv[nombre] -= cantidad
        if inv[nombre] <= 0:
            del inv[nombre]
        guardar_json(inventarios, INVENTARIO_PATH)
        await ctx.send(f"❌ Quitado {cantidad}x {nombre} a {miembro.display_name}.")
    else:
        await ctx.send("Ese usuario no tiene esa cantidad de ese ítem.")

@bot.command()
async def cambiarsalud(ctx, miembro: discord.Member, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    stats = stats_data.setdefault(uid, {"salud": 100, "mana": 50})
    stats["salud"] = cantidad
    stats["salud_max"] = cantidad
    guardar_json(stats_data, STATS_PATH)
    await ctx.send(f"❤️ Salud actual y máxima de {miembro.display_name} cambiada a {cantidad}.")

@bot.command()
async def cambiarmana(ctx, miembro: discord.Member, cantidad: int):
    if not es_master(ctx):
        return await ctx.send("❌ Solo el master puede usar esto.")
    uid = str(miembro.id)
    stats = stats_data.setdefault(uid, {"salud": 100, "mana": 50})
    stats["mana"] = cantidad
    stats["mana_max"] = cantidad
    guardar_json(stats_data, STATS_PATH)
    await ctx.send(f"🔷 Maná actual y máximo de {miembro.display_name} cambiado a {cantidad}.")
# === Parte final del archivo bot.py ===

# Cargar datos al iniciar
inventarios = cargar_json(INVENTARIO_PATH)
recetas = cargar_json(RECETAS_PATH)
tienda = cargar_json(TIENDA_PATH)
stats_data = cargar_json(STATS_PATH)


bot.run(os.getenv("DISCORD_TOKEN"))
