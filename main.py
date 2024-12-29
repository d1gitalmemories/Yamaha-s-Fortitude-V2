from flask import Flask, request, jsonify
import discord
from discord.ext import commands
import asyncio
import threading
import platform
import sys
import time
import os
import requests
import json
from discord import app_commands
import logging

apiURL = "http://venus.hidencloud.com:25621"

app = Flask(__name__)

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='g!', intents=intents)

bot_loop = asyncio.get_event_loop()
queue = asyncio.Queue()

holykurumi = 1297181112606392372
truemember = 1297188609777991681
praychannel = 1297187675945832448

roblox_users = {}
discord_role_update_data = {}

USER_TIMEOUT = 30 * 1000  

def in_channel(channel_id):
    async def predicate(interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.channels, id=channel_id)
            if interaction.channel.id != channel_id:
                await interaction.response.send_message(
                    '> :no_entry: Ze holy command shall be used in its rightful place only! -glares-', 
                    ephemeral=True
                )
                return False  
            return True
        except Exception as e:
            logging.error(f'Error in channel check: {e}')
            await interaction.response.send_message(
                'An unexpected error occurred while checking permissions.', 
                ephemeral=True
            )
            return False  
    return app_commands.check(predicate)

def has_role(role_id):
    async def predicate(interaction: discord.Interaction):
        try:
            role = discord.utils.get(interaction.guild.roles, id=role_id)
            if role not in interaction.user.roles:
                await interaction.response.send_message(
                    '> :no_entry: Only the chosen ones with the sacred role may use this command! -glares-', 
                    ephemeral=True
                )
                return False  
            return True
        except Exception as e:
            logging.error(f'Error in role check: {e}')
            await interaction.response.send_message(
                'An unexpected error occurred while checking roles.', 
                ephemeral=True
            )
            return False  
    return app_commands.check(predicate)


def in_user(user_id):
    async def predicate(interaction: discord.Interaction):
        try:
            if interaction.user.id != user_id:
                await interaction.response.send_message(
                    '> :no_entry: Ze holy command is reserved for a chosen one, not you! -glares-', 
                    ephemeral=True
                )
                return False  
            return True
        except Exception as e:
            logging.error(f'Error in user check: {e}')
            await interaction.response.send_message(
                'An unexpected error occurred while checking user permissions.', 
                ephemeral=True
            )
            return False  
    return app_commands.check(predicate)


def get_user_id_and_check_group(roblox_username, group_id):
    # Fetch Roblox user ID
    user_id_response = requests.post(
        "https://users.roblox.com/v1/usernames/users",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"usernames": [roblox_username], "excludeBannedUsers": True}
    )
    if user_id_response.status_code != 200 or not user_id_response.json().get("data"):
        return None, False  # User not found

    roblox_user_id = user_id_response.json()["data"][0]["id"]

    # Check if user is in the group
    url = f"https://groups.roblox.com/v1/users/{roblox_user_id}/groups/roles"
    response = requests.get(url)
    
    if response.status_code == 200:
        user_groups = response.json().get("data", [])
        for group in user_groups:
            if group["group"]["id"] == group_id:
                return roblox_user_id, True  # User found and is in the group
    return roblox_user_id, False  # User found but not in the group

def load_json(file_path):
    try:
        with open(f"database/{file_path}", 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return [] 

def cleanup_old_users():
    while True:
        now = time.time() * 1000  

        
        roblox_users_copy = roblox_users.copy()
        for username, user_data in roblox_users_copy.items():
            if now - user_data['timestamp'] > USER_TIMEOUT:
                del roblox_users[username]

        
        role_updates_copy = discord_role_update_data.copy()
        for username, user_data in role_updates_copy.items():
            if now - user_data['timestamp'] > USER_TIMEOUT:
                del discord_role_update_data[username]

        time.sleep(10)  

cookie = None
guildID = None
ROBLOX_GROUP_ID = None
bot_token = None
acolyte = None

def read_config(file_path):
    global cookie, guildID, ROBLOX_GROUP_ID, bot_token, acolyte
    
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
            
            cookie = config.get('robloxcookie')
            guildID = config.get('guildID')
            ROBLOX_GROUP_ID = config.get('groupid')
            bot_token = config.get('discordtoken')
            acolyte = config.get('acolyteID')
            
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError:
        print("Error: The file is not a valid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

read_config("config.json")
guild = discord.Object(id=guildID)

@bot.command(name="sync")
@in_channel(holykurumi)
async def sync(ctx):
    try:
        await ctx.message.delete()
        synced = await bot.tree.sync(guild=guild)
        msg = await ctx.send(f'Synced {len(synced)} commands.')
        await asyncio.sleep(3)
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.event
async def on_ready():
    os.system("clear")
    system_info = {
        "Bot Name": bot.user.name,
        "Bot ID": bot.user.id,
        "Discord.py Version": discord.__version__,
        "Operating System": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "Network Name": platform.node(),
        "OS Version": platform.version(),
        "Python Version": sys.version,
    }
    
    print("\n" + "="*40)
    print(" Bot Information ".center(40, "="))
    print("="*40)
    
    for key, value in system_info.items():
        print(f"{key:20}: {value}")
    
    print("="*40 + "\n")

def getXsrf():
    authurl = "https://auth.roblox.com/v2/login"
    xsrfRequest = requests.post(authurl, cookies={'.ROBLOSECURITY': cookie})
    return xsrfRequest.headers["x-csrf-token"]

def change_rank_in_roblox(group_id, roblox_username, role_id):
    url = 'https://users.roblox.com/v1/usernames/users'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {'usernames': [roblox_username], 'excludeBannedUsers': True}
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        response_json = response.json()
        if 'data' in response_json and len(response_json['data']) > 0:
            user_id = response_json['data'][0]['id']
        else:
            print("User not found or banned.")
            return
    else:
        print("Failed to fetch user ID.")
        return

    xsrf = getXsrf()
    url = f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}"
    request_body = {"roleId": role_id}
    response = requests.patch(
        url,
        headers={
            "Cookie": ".ROBLOSECURITY=" + cookie,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-CSRF-TOKEN": xsrf
        },
        json=request_body
    )
    
    if response.status_code == 200:
        print("Role updated successfully.")
    else:
        print(f"Failed to update role. Status code: {response.status_code}")

@bot.tree.command(name="changerank", description="Change rank of a user. See pins on how to use it.", guild=guild)
@in_channel(holykurumi)
async def changerank(interaction: discord.Interaction, robloxusername: str, rankname: str):
    with open('database/correspondingroles.json') as f:
        corresponding_roles = json.load(f)

    
    await interaction.response.defer(ephemeral=True)

    
    if rankname not in corresponding_roles:
        await interaction.followup.send(f"Invalid rank: {rankname}.")
        return
    
    next_roblox_role_id = corresponding_roles[rankname]

    change_rank_in_roblox(ROBLOX_GROUP_ID, robloxusername, next_roblox_role_id)

    await interaction.followup.send(f"> 🔮 {robloxusername}'s rank has been changed to {rankname}. Make sure to update via Bloxlink, MWAH!")

@app.route('/api/discordRoleUpdate/<robloxUsername>', methods=['GET'])
def discord_role_update(robloxUsername):
    data = discord_role_update_data.get(robloxUsername)
    if data:
        return jsonify(data), 200
    return jsonify({'message': 'No role update found for this user.'}), 404
    

@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.json
    discordId = data.get('discordId')
    robloxUsername = data.get('robloxUsername')

    if discordId and robloxUsername:
        roblox_users[robloxUsername] = {'discordId': discordId, 'timestamp': time.time() * 1000}
        return jsonify({'message': 'Username received, waiting for Roblox player.'}), 200
    return jsonify({'message': 'Invalid data received.'}), 400

@app.route('/api/role', methods=['POST'])
def update_role():
    data = request.json
    robloxUsername = data.get('robloxUsername')
    roleId = data.get('roleId')

    if robloxUsername and roleId:
        discord_role_update_data[robloxUsername] = {'roleId': roleId, 'timestamp': time.time() * 1000}
        
        bot_loop.create_task(queue.put((robloxUsername, roleId)))
        return jsonify({'message': 'Role received, processing in Discord.'}), 200
    return jsonify({'message': 'Invalid data received.'}), 400

@app.route('/api/shouldShowGui/<robloxUsername>', methods=['GET'])
def should_show_gui(robloxUsername):
    print("Checking GUI for user:", robloxUsername)  
    user = roblox_users.get(robloxUsername)
    if user:
        user['timestamp'] = time.time() * 1000  
        return jsonify({'showGui': True}), 200
    return jsonify({'showGui': False}), 404

@bot.tree.command(name="pray", description="Pray for your true membership!", guild=discord.Object(id=guildID))
@in_channel(praychannel)
async def register(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer the initial response
    
    global global_discord_id
    global current_roblox_username
    global update_task

    global_discord_id = interaction.user.id
    current_roblox_username = interaction.user.nick

    roblox_user_id, is_in_group = get_user_id_and_check_group(current_roblox_username, ROBLOX_GROUP_ID)
    if not roblox_user_id:
        await interaction.followup.send(
            f"❌ Could not find **{current_roblox_username}** on Roblox. -glares-"
        )
        current_roblox_username = None
        update_task = None
        return
    if not is_in_group:
        await interaction.followup.send(
            f"❌ **{current_roblox_username}** is not in ze sacred Roblox group! -gasps-"
        )
        current_roblox_username = None
        update_task = None
        return

    response = requests.post('http://venus.hidencloud.com:25621/api/verify', json={
        'discordId': global_discord_id,
        'robloxUsername': current_roblox_username
    })

    if response.status_code == 200:
        await interaction.followup.send(
            f'> :trident: Praying for **{current_roblox_username}** to ascend to ze true membership! Please return to ze sacred [ranking menu](https://www.roblox.com/games/96180822251796/Ranking-Centre) and select your desired rank!'
        )
        update_task = asyncio.create_task(update_role_and_nickname(interaction))
    else:
        await interaction.followup.send(
            f'> Unable to hear your holy prayers! Try again later! -gasps-'
        )

async def update_role_and_nickname(interaction: discord.Interaction):
    global current_roblox_username
    global update_task
    global global_discord_id

    success_channel_id = 1297183617029771345  
    success_channel = interaction.guild.get_channel(success_channel_id)

    start_time = time.time()  # Record the start time

    while current_roblox_username:
        # Check if 30 seconds have passed
        if time.time() - start_time > 30:
            current_roblox_username = None
            update_task = None
            return

        try:
            response = requests.get(f'http://venus.hidencloud.com:25621/api/discordRoleUpdate/{current_roblox_username}')
            if response.status_code == 200:
                role_data = response.json()
                role_id = role_data['roleId']

                change_rank_in_roblox(ROBLOX_GROUP_ID, current_roblox_username, role_id)

                roles_mapping = load_json("roles.json")
                discord_role_id = roles_mapping.get(str(role_id))

                if discord_role_id:
                    guild = interaction.guild
                    role = discord.utils.get(guild.roles, id=int(discord_role_id))
                    supporterrole = discord.utils.get(guild.roles, id=int(acolyte))
                    truememberrole = discord.utils.get(guild.roles, id=int(truemember))
                    if role:
                        member = guild.get_member(interaction.user.id)
                        if member:
                            await member.add_roles(role)
                            await member.add_roles(truememberrole)
                            await member.remove_roles(supporterrole)
                            await success_channel.send(
                                f'> 🔮 AH! Blessed be ze ascension of <@{global_discord_id}>! Welcome to your new home!'
                            )
                        else:
                            await interaction.followup.send(
                                f'❌ Zis is tragic! I could not find ze user in ze guild!'
                            )
                    else:
                        await interaction.followup.send(
                            f'❌ Sacré bleu! Ze Discord role is missing!'
                        )
                else:
                    await interaction.followup.send(
                        f'❌ Ze mapping for ze Roblox role is nowhere to be found!'
                    )

                current_roblox_username = None
                update_task = None 
                return

            else:
                print(f"Failed to get role data: {response.status_code}")

        except Exception as e:
            print(f"Error in update_role_and_nickname: {e}")

        await asyncio.sleep(5)

async def process_queue():
    while True:
        roblox_username, role_id = await queue.get()
        await handle_role_update(roblox_username, role_id)
        queue.task_done()

async def handle_role_update(roblox_username, role_id):
    guild = bot.get_guild(guildID)
    discord_role_id = load_json("roles.json").get(str(role_id))
    role = discord.utils.get(guild.roles, id=int(discord_role_id))
    
    if role:
        member = discord.utils.get(guild.members, name=roblox_username)
        if member:
            await member.add_roles(role)
            supporter_role = discord.utils.get(guild.roles, id=int(acolyte))
            if supporter_role:
                await member.remove_roles(supporter_role)
            print(f"Role {role_id} assigned to {roblox_username}")
        else:
            print(f"Member not found: {roblox_username}")
    else:
        print(f"Role not found: {role_id}")

def run_flask():
    app.run(host='0.0.0.0', port=25621)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    cleanup_thread = threading.Thread(target=cleanup_old_users, daemon=True)
    cleanup_thread.start()
    flask_thread.start()
    bot.run(bot_token)