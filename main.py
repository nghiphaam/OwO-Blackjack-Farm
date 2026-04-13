"""
This code is only made for educational and practice purposes.
Author and Async Development are not responsible for misuse.

GhoSty OwO BlackJack V2 Stable Build
Stable Alpha Build Version: 120426.2.0.0

GitHub: https://github.com/WannaBeGhoSt
Discord: https://discord.gg/SyMJymrV8x
"""

import discord
from discord import emoji
from discord.ext import commands
from colorama import Fore, Style, init as colorama_init
import asyncio, json, re, os, time, unicodedata, sys
from datetime import datetime
import random

colorama_init()

if sys.version_info >= (3, 10):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
else:
    loop = asyncio.get_event_loop()

ghostyop = discord.Intents.all()
GhoStyyy = "."
ghosty = commands.Bot(
    command_prefix=GhoStyyy, case_insensitive=True, self_bot=True, intents=ghostyop, loop=loop
)
ghosty.remove_command("help")

@ghosty.event
async def on_ready():
    print(
        f"{Fore.LIGHTRED_EX} > GhoSty OwO BlackJack Farm v2 Connected To:{Style.RESET_ALL}",
        f"{Fore.LIGHTGREEN_EX}{ghosty.user}{Style.BRIGHT}{Style.RESET_ALL}",
    )
    print(f"{Fore.LIGHTRED_EX} > Released - 12 April 2026 [Join Async Development For Further Updates]{Style.RESET_ALL}")
    print(f"{Fore.CYAN} > https://discord.gg/SyMJymrV8x {Style.RESET_ALL}")

farming_active = False
farm_task = None
DATA_FILE = "data.json"
OWO_BOT_ID = 408785106942164992

def parse_time_to_seconds(time_str):
    seconds = 0
    time_str = time_str.lower()
    hours = re.search(r'(\d+)h', time_str)
    mins = re.search(r'(\d+)m', time_str)
    secs = re.search(r'(\d+)s', time_str)
    if hours: seconds += int(hours.group(1)) * 3600
    if mins: seconds += int(mins.group(1)) * 60
    if secs: seconds += int(secs.group(1))
    return seconds

def parse_amount(amt_str):
    amt_str = amt_str.lower().replace(",", "")
    if amt_str.endswith('k'):
        return int(float(amt_str[:-1]) * 1000)
    elif amt_str.endswith('m'):
        return int(float(amt_str[:-1]) * 1000000)
    else:
        return int(amt_str)

DEFAULT_TIMING_RANGES = {
    "pre_round": (1.1, 2.6),
    "embed_poll": (0.9, 1.6),
    "balance_poll": (1.0, 1.7),
    "warning_retry": (0.7, 1.2),
    "in_round_poll": (1.0, 2.2),
    "state_repeat": (0.7, 1.3),
    "unknown_footer": (1.1, 2.0),
    "repeat_react": (0.18, 0.45),
    "post_react": (1.1, 2.4),
    "empty_embed_retry": (2.0, 3.5),
    "post_round": (1.2, 2.4),
    "farm_error": (2.0, 3.8),
}

def load_config():
    defaults = {
        "TOKEN": "",
        "BET_SEQUENCE": "Low",
        "REACT_STALL_TIMEOUT_SECONDS": 6,
        "DYNAMIC_TIMING": True,
        "TIMING_RANGES": DEFAULT_TIMING_RANGES,
    }
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            loaded = json.load(f)
        defaults.update(loaded)
        return defaults
    return defaults

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "start_timestamp": None,
        "starting_balance": 0,
        "current_balance": 0,
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "commands_used": 0,
        "seq_index": 0,
        "timer_end": None,
        "stop_on_loss_limit": None,
        "internal_profit": 0
    }

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

data = load_data()
data["timer_end"] = None
save_data(data)
config = load_config()
TIMING_RANGES = config.get("TIMING_RANGES", DEFAULT_TIMING_RANGES)

BET_SEQUENCES = {
    "Low": [488, 976, 1952, 3904, 7808, 15616, 31232, 62464, 124928, 249856],
    "High": [10000, 25000, 50000, 100000, 180000, 240000] # not recommended due to higher risk of hitting max bet limit, but included for variety
}

def dynamic_delay(label, minimum=None, maximum=None):
    if minimum is None or maximum is None:
        minimum, maximum = TIMING_RANGES[label]
    return random.uniform(minimum, maximum)

def parse_balance(text):
    match = re.search(r'__([\d,]+)__\s*cowoncy', text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    match = re.search(r'([\d,]+)\s*cowoncy', text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    return None

def extract_rank(card_str):
    token = re.sub(r"[^a-z0-9]", "", str(card_str).lower())
    if not token:
        return None

    if token.startswith("10") or token.startswith("t"):
        return 10
    if token.startswith("a") or token == "1":
        return 'A'
    if token.startswith(("j", "q", "k")):
        return 10

    rank_part = re.search(r"\d+", token)
    if not rank_part:
        return None

    value = int(rank_part.group(0))
    if value == 1:
        return 'A'
    if 2 <= value <= 10:
        return value
    return None

def hand_value(cards):
    values = []
    aces = 0
    for c in cards:
        if c == 'A':
            aces += 1
            values.append(11)
        else:
            values.append(c)
    total = sum(values)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    soft = (aces > 0 and total <= 21)
    return total, soft

def dealer_upcard_value(dealer_upcard):
    if dealer_upcard == 'A':
        return 11
    return dealer_upcard if isinstance(dealer_upcard, int) else 10

HARD_ACTION_TABLE = {
    4:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    5:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    6:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    7:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    8:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    9:  {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    10: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    11: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    12: {2: 'hit', 3: 'hit', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    13: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    14: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    15: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    16: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    17: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    18: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    19: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    20: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    21: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
}

SOFT_ACTION_TABLE = {
    13: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    14: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    15: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    16: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    17: {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    18: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'hit', 10: 'hit', 11: 'hit'},
    19: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    20: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    21: {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
}

PAIR_ACTION_TABLE = {
    (2, 2): {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (3, 3): {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (4, 4): {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (5, 5): {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (6, 6): {2: 'hit', 3: 'hit', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (7, 7): {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (8, 8): {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
    (9, 9): {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    (10, 10): {2: 'stand', 3: 'stand', 4: 'stand', 5: 'stand', 6: 'stand', 7: 'stand', 8: 'stand', 9: 'stand', 10: 'stand', 11: 'stand'},
    ('A', 'A'): {2: 'hit', 3: 'hit', 4: 'hit', 5: 'hit', 6: 'hit', 7: 'hit', 8: 'hit', 9: 'hit', 10: 'hit', 11: 'hit'},
}

def classify_hand(cards, total, soft):
    if len(cards) == 2 and cards[0] == cards[1]:
        return "pair", (cards[0], cards[1])
    if soft:
        return "soft", total
    return "hard", total

def basic_strategy(cards, player_total, dealer_upcard, soft):
    dealer_val = dealer_upcard_value(dealer_upcard)
    hand_type, hand_key = classify_hand(cards, player_total, soft)

    if hand_type == "pair":
        pair_action = PAIR_ACTION_TABLE.get(hand_key, {}).get(dealer_val)
        if pair_action is not None:
            return pair_action, f"pair {hand_key[0]}-{hand_key[1]} vs {dealer_upcard}"

    if hand_type == "soft":
        if player_total <= 12:
            return 'hit', f"soft {player_total} vs {dealer_upcard}"
        if player_total >= 21:
            return 'stand', f"soft {player_total} vs {dealer_upcard}"
        action = SOFT_ACTION_TABLE.get(player_total, SOFT_ACTION_TABLE[20]).get(dealer_val, 'hit')
        return action, f"soft {player_total} vs {dealer_upcard}"

    if player_total <= 4:
        return 'hit', f"hard {player_total} vs {dealer_upcard}"
    if player_total >= 21:
        return 'stand', f"hard {player_total} vs {dealer_upcard}"
    action = HARD_ACTION_TABLE.get(player_total, HARD_ACTION_TABLE[20]).get(dealer_val, 'hit')
    return action, f"hard {player_total} vs {dealer_upcard}"

def parse_displayed_player_total(text):
    for line in text.splitlines():
        matches = re.findall(r"([^\[\]\n]+?)\s+\[(\d+)\*?\]", line)
        for name, total_str in matches:
            if "dealer" in name.lower():
                continue
            return int(total_str)
    return None

def decide(text):
    try:
        clean = text.replace("`", "")

        dealer_rank, player_values, soft = parse_game_state(clean)
        if dealer_rank is None or not player_values:
            print(f"{Fore.YELLOW}[SAFETY] Incomplete parsed state, waiting for refresh.{Style.RESET_ALL}")
            return None, 0

        total, soft = hand_value(player_values)
        displayed_total = parse_displayed_player_total(clean)
        if displayed_total is not None and displayed_total != total:
            print(
                f"{Fore.YELLOW}[SAFETY] Parsed total {total} does not match displayed total {displayed_total}, waiting for refresh.{Style.RESET_ALL}"
            )
            return None, displayed_total

        action, reason = basic_strategy(player_values, total, dealer_rank, soft)
        print(f"{Fore.YELLOW}[DECIDE] Cards={player_values} total={total} soft={soft} dealer={dealer_rank} {reason} → {action}{Style.RESET_ALL}")
        return action, total
    except Exception as e:
        print(f"{Fore.RED}[DECIDE ERROR] {e}{Style.RESET_ALL}")
        return None, 0

def parse_game_state(text):
    card_pattern = r":([^:]+):"
    dealer_match = re.search(r"Dealer \[([^+?]+)\+?\?\]", text)
    if not dealer_match:
        raise ValueError("Could not find dealer upcard")
    dealer_rank_str = dealer_match.group(1).strip()
    dealer_rank = extract_rank(dealer_rank_str)

    lines = text.splitlines()
    player_cards = []
    for i, line in enumerate(lines):
        if re.search(r"\[\d+\*?\]", line) and not re.search(r"[Dd]ealer", line):
            for j in range(i + 1, len(lines)):
                current_line = lines[j]
                if re.search(r"[Dd]ealer", current_line):
                    break
                if current_line.strip().startswith("```") or "game in progress" in current_line.lower():
                    break

                card_matches = re.findall(card_pattern, current_line)
                if card_matches:
                    player_cards.extend(card_matches)
                    continue

                if player_cards and current_line.strip():
                    break
            break

    if not player_cards:
        all_cards = re.findall(card_pattern, text)
        player_cards = [c for c in all_cards if c not in ["cardback", dealer_rank_str] and "?" not in c]

    values = []
    for card in player_cards:
        try:
            rank = extract_rank(card)
            values.append(rank)
        except Exception:
            continue

    total, soft = hand_value(values)
    return dealer_rank, values, soft

def get_owo_text(msg):
    parts = []
    if msg.content:
        parts.append(msg.content)
    if msg.embeds:
        embed = msg.embeds[0]
        if embed.author and embed.author.name:
            parts.append(embed.author.name)
        if embed.description:
            parts.append(embed.description)
        for field in embed.fields:
            if field.name:
                parts.append(field.name)
            if field.value:
                parts.append(field.value)
        if embed.footer and embed.footer.text:
            parts.append(embed.footer.text)
    return "\n".join(parts)

async def wait_for_new_owo_embed(ctx, last_owo_id=None, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            history = await ctx.channel.history(limit=10).flatten()
            for m in history:
                if m.author.id != OWO_BOT_ID:
                    continue
                if last_owo_id and m.id <= last_owo_id:
                    continue
                if not m.embeds:
                    continue
                return m
        except Exception as e:
            print(f"{Fore.RED}[wait error] {e}{Style.RESET_ALL}")
        await asyncio.sleep(dynamic_delay("embed_poll"))
    return None

async def start_blackjack_round(ctx, bet):
    last_owo_id = None
    try:
        pre_history = await ctx.channel.history(limit=10).flatten()
        for m in pre_history:
            if m.author.id == OWO_BOT_ID:
                last_owo_id = m.id
                break
    except Exception as e:
        print(f"{Fore.RED}[snapshot error] {e}{Style.RESET_ALL}")

    await asyncio.sleep(dynamic_delay("embed_poll", 0.6, 1.3))
    await ctx.send(f"owo bj {bet}")
    return await wait_for_new_owo_embed(ctx, last_owo_id=last_owo_id, timeout=15)

async def fetch_owo_balance(ctx):
    last_owo_id = None
    try:
        pre_history = await ctx.channel.history(limit=10).flatten()
        for m in pre_history:
            if m.author.id == OWO_BOT_ID:
                last_owo_id = m.id
                break
    except Exception as e:
        print(f"{Fore.RED}[snapshot error] {e}{Style.RESET_ALL}")

    await ctx.send("owo cash")

    for attempt in range(10):
        await asyncio.sleep(dynamic_delay("balance_poll"))
        try:
            messages = await ctx.channel.history(limit=10).flatten()
            for msg in messages:
                if msg.author.id != OWO_BOT_ID:
                    continue
                if last_owo_id and msg.id <= last_owo_id:
                    continue
                text = get_owo_text(msg)
                if "cowoncy" in text.lower():
                    balance = parse_balance(text)
                    if balance is not None:
                        print(f"{Fore.GREEN}[BALANCE] Fetched: {balance:,}{Style.RESET_ALL}")
                        return balance
        except Exception as e:
            print(f"{Fore.RED}[fetch error] {e}{Style.RESET_ALL}")

    print(f"{Fore.RED}[BALANCE] No fresh cowoncy response found.{Style.RESET_ALL}")
    return None

async def check_warning(ctx):
    if not farming_active:
        return True
    for attempt in range(2):
        try:
            messages = await ctx.channel.history(limit=15).flatten()
            for msg in messages:
                if msg.author.id != OWO_BOT_ID:
                    continue
                msg_content = str(msg.content)
                if not msg_content:
                    continue
                clean = unicodedata.normalize("NFKC", msg_content)
                clean = re.sub(r'[\u200B-\u200D\uFEFF]', '', clean).lower()
                if "captcha" in clean and "verify" in clean:
                    match = re.search(r'[\(\[\{]?\s*(\d+)\s*[\/／]\s*5\s*[\)\]\}]?', clean)
                    if match:
                        count = int(match.group(1))
                        print(f"{Fore.YELLOW}⚠️ CAPTCHA WARNING DETECTED: ({count}/5){Style.RESET_ALL}")
                        if count == 1:
                            return True
            return False
        except Exception as e:
            status = getattr(e, "status", None)
            error_text = str(e).lower()
            is_transient = status in {500, 502, 503, 504} or "503 service unavailable" in error_text or "connection termination" in error_text
            if is_transient and attempt == 0:
                print(f"{Fore.YELLOW}[warning check] transient upstream error, retrying...{Style.RESET_ALL}")
                await asyncio.sleep(dynamic_delay("warning_retry"))
                continue
            if is_transient:
                print(f"{Fore.YELLOW}[warning check] transient upstream error, skipping this scan.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Warning check error: {e}{Style.RESET_ALL}")
            return False

async def run_farm(ctx):
    global farming_active, data, config, TIMING_RANGES

    farming_active = True
    print(f"{Fore.GREEN}[FARM] Started.{Style.RESET_ALL}")

    seq_idx = data.get("seq_index", 0)

    while farming_active:
        try:
            if data.get("timer_end") and time.time() >= data["timer_end"]:
                if seq_idx == 0:
                    farming_active = False
                    data["timer_end"] = None
                    save_data(data)
                    await ctx.send("⏳ **Timer ended!** Farm stopped safely after a win.")
                    print(f"{Fore.YELLOW}[TIMER] Farm stopped naturally.{Style.RESET_ALL}")
                    return
                else:
                    print(f"{Fore.YELLOW}[TIMER] Time is up, but currently in a losing streak. Playing until next win to stop.{Style.RESET_ALL}")
            cfg = load_config()
            seq_name = cfg.get("BET_SEQUENCE", "Low")
            sol_limit = data.get("stop_on_loss_limit")
            if not sol_limit:
                sol_limit = 499224 if seq_name == "Low" else 605000

            if data.get("internal_profit", 0) < 0 and abs(data["internal_profit"]) >= sol_limit:
                farming_active = False
                await ctx.send(f"🛑 **Stop-on-Loss Triggered!** Net loss reached **__{abs(data['internal_profit']):,}__**. Farm stopped.")
                print(f"{Fore.RED}[STOP ON LOSS] Farm stopped due to max loss limit.{Style.RESET_ALL}")
                return

            if await check_warning(ctx):
                farming_active = False
                print(f"{Fore.RED}[FARM] Stopped: CAPTCHA WARNING.{Style.RESET_ALL}")
                await ctx.send("⚠️ **__WARNING DETECTED!__** 🛑 Stopping | **SOLVE YOUR CAPTCHA FIRST** | Type `.start` again to restart.")
                return

            config = cfg
            TIMING_RANGES = cfg.get("TIMING_RANGES", DEFAULT_TIMING_RANGES)
            sequence = BET_SEQUENCES.get(seq_name, BET_SEQUENCES["Low"])
            react_stall_timeout = float(cfg.get("REACT_STALL_TIMEOUT_SECONDS", 8))

            if seq_idx >= len(sequence):
                seq_idx = 0

            bet = sequence[seq_idx]
            data["commands_used"] += 1
            save_data(data)

            await asyncio.sleep(dynamic_delay("pre_round"))
            print(f"{Fore.CYAN}[ROUND] Betting {bet:,} | idx={seq_idx} | seq={seq_name}{Style.RESET_ALL}")
            msg = await start_blackjack_round(ctx, bet)

            if not msg:
                print(f"{Fore.YELLOW}[FARM] No OwO embed found, retrying round...{Style.RESET_ALL}")
                await asyncio.sleep(dynamic_delay("empty_embed_retry"))
                continue
            last_reaction = None
            last_action_state = None
            last_action_time = 0.0

            while farming_active:
                if await check_warning(ctx):
                    farming_active = False
                    await ctx.send("⚠️ **__CAPTCHA WARNING!__** Stopped. Solve & restart.")
                    return


                try:
                    await asyncio.sleep(dynamic_delay("in_round_poll"))
                    history = await ctx.channel.history(limit=10).flatten()
                    for m in history:
                        if m.id == msg.id:
                            msg = m
                            break
                except Exception as e:
                    print(f"{Fore.RED}[refetch error] {e}{Style.RESET_ALL}")

                full_text = get_owo_text(msg)

                footer = ""
                if msg.embeds and msg.embeds[0].footer:
                    footer = msg.embeds[0].footer.text or ""
                footer_lower = footer.lower().strip()

                if "game in progress" not in footer_lower and "resuming previous game" not in footer_lower:
                    if "won" in footer_lower and "lost" not in footer_lower:
                        data["wins"] += 1
                        data["internal_profit"] = data.get("internal_profit", 0) + bet
                        seq_idx = 0
                        print(f"{Fore.GREEN}[WIN] +{bet:,} → reset to idx 0{Style.RESET_ALL}")
                        data["seq_index"] = seq_idx
                        save_data(data)
                        break
                    elif "tied" in footer_lower or "both bust" in footer_lower:
                        data["ties"] += 1
                        print(f"{Fore.YELLOW}[TIE] {bet:,} → same idx {seq_idx}{Style.RESET_ALL}")
                        data["seq_index"] = seq_idx
                        save_data(data)
                        break
                    elif "lost" in footer_lower or ("bust" in footer_lower and "both" not in footer_lower):
                        data["losses"] += 1
                        data["internal_profit"] = data.get("internal_profit", 0) - bet
                        seq_idx += 1
                        print(f"{Fore.RED}[LOSS] -{bet:,} → next idx {seq_idx}{Style.RESET_ALL}")
                        data["seq_index"] = seq_idx
                        save_data(data)
                        break
                    else:
                        await asyncio.sleep(dynamic_delay("unknown_footer"))
                        continue


                state_key = re.sub(r"\s+", " ", full_text).strip()
                if state_key == last_action_state:
                    if last_action_time and (time.time() - last_action_time) >= react_stall_timeout:
                        print(f"{Fore.YELLOW}[STALL] No state change after {react_stall_timeout:.1f}s. Reissuing blackjack bet {bet:,}.{Style.RESET_ALL}")
                        data["commands_used"] += 1
                        save_data(data)
                        msg = await start_blackjack_round(ctx, bet)
                        last_reaction = None
                        last_action_state = None
                        last_action_time = 0.0
                        if not msg:
                            print(f"{Fore.YELLOW}[STALL] Retry round did not return a fresh embed, retrying outer loop...{Style.RESET_ALL}")
                            break
                        continue
                    await asyncio.sleep(dynamic_delay("state_repeat"))
                    continue

                action, _ = decide(full_text)
                if action is None:
                    await asyncio.sleep(dynamic_delay("state_repeat"))
                    continue

                emoji = "👊" if action == "hit" else "🛑"

                if last_reaction == emoji:
                    try:
                        await msg.remove_reaction(emoji, ghosty.user)
                        last_reaction = None
                        last_action_state = state_key
                        last_action_time = time.time()
                        data["commands_used"] += 1
                        save_data(data)
                        await asyncio.sleep(dynamic_delay("repeat_react"))
                        continue
                    except Exception as e:
                        print(f"{Fore.RED}[remove reaction error] {e}{Style.RESET_ALL}")

                try:
                    await msg.add_reaction(emoji)
                    last_reaction = emoji
                    last_action_state = state_key
                    last_action_time = time.time()
                except Exception as e:
                    print(f"{Fore.RED}[react error] {e}{Style.RESET_ALL}")

                data["commands_used"] += 1
                save_data(data)
                await asyncio.sleep(dynamic_delay("post_react"))

            await asyncio.sleep(dynamic_delay("post_round"))
        except Exception as e:
            print(f"{Fore.RED}[FARM ERROR] {e}{Style.RESET_ALL}")
            await asyncio.sleep(dynamic_delay("farm_error"))
    print(f"{Fore.YELLOW}[FARM] Stopped.{Style.RESET_ALL}")

@ghosty.command()
async def start(ctx):
    global farming_active, farm_task, data
    if farming_active:
        return await ctx.send("⚠️ **GhoSty OwO BlackJack Worker is already running!**\n\n🛑 Please use `.stop` first, then `.start` to restart/force fix the worker.\nJoin the support server for better guidance.")
    print(f"{Fore.CYAN}[START] Initializing...{Style.RESET_ALL}")

    balance = await fetch_owo_balance(ctx)
    if balance is None:
        return await ctx.send("❌ Failed to fetch owo cash balance. Join the support server Async Development for troubleshooting.")
    data["starting_balance"] = balance
    data["current_balance"] = balance
    data["start_timestamp"] = datetime.now().isoformat()
    data["wins"] = 0
    data["losses"] = 0
    data["ties"] = 0
    data["commands_used"] = 0
    data["seq_index"] = 0
    data["internal_profit"] = 0
    save_data(data)

    print(f"{Fore.GREEN}[START] Balance saved: {balance:,}{Style.RESET_ALL}")
    await ctx.send(f"✅ GhoSty OwO BlackJack Farm Running. Starting balance: **__{balance:,}__** cowoncy.")

    farm_task = ghosty.loop.create_task(run_farm(ctx))

@ghosty.command()
async def stop(ctx):
    global farming_active, data
    if not farming_active:
        return await ctx.send("⏹ GhoSty OwO BlackJack Worker is not running.")
    farming_active = False
    data["timer_end"] = None
    save_data(data)
    await ctx.send("🛑 **__Stopped__** successfully. Timer also cleared if active.")
    print(f"{Fore.YELLOW}[STOP] User halted farm.{Style.RESET_ALL}")

@ghosty.command()
async def timer(ctx, *, time_input=None):
    global data
    if not time_input:
        return await ctx.send("⚙️ Usage: `.timer 1h 30m 20s`, `.timer 45m`, etc.")

    seconds = parse_time_to_seconds(time_input)
    if seconds < 300:
        return await ctx.send("❌ Error: Minimum timer duration allowed is 5 minutes.")

    data["timer_end"] = time.time() + seconds
    save_data(data)
    await ctx.send(f"✅ Timer set for **{time_input}**. Farm will naturally stop after this time (and after winning the active sequence streak).")

@ghosty.command()
async def stoponloss(ctx, amount_str=None):
    global data
    if not amount_str:
        return await ctx.send("⚙️ Usage: `.stoponloss 100k`, `.stoponloss 1m`, `.stoponloss 500k`")

    try:
        limit = parse_amount(amount_str)
        if limit < 100000:
            return await ctx.send("❌ Error: Minimum stop on loss amount allowed is 100k.")

        data["stop_on_loss_limit"] = limit
        save_data(data)
        await ctx.send(f"✅ Stop on Loss limit set successfully to **__{limit:,}__** cowoncy.")
    except Exception:
        await ctx.send("❌ Invalid format! Please use formats like `500k`, `1m`, `100k`, etc.")

@ghosty.command(aliases=["h"])
async def help(ctx):
    ghosty_help = """
    # 🤑 GhoSty OwO BlackJack Farm V2 🤑
Prefix: `.`

**__Main__**
 🌟 Start: *Starts The AutoBot*
 🛑 Stop: *Stops The AutoBot*
 🔍 Status: *Shows Bot Status*
 ⚡ Bets: *Change bet sequence (Low/High)*
 ⏳ Timer: *Set duration to auto-stop (.timer 45m)*
 📉 StopOnLoss: *Set max loss limit (.stoponloss 1m)*

**__Features__**
 ⚠ Ban Bypass
 🚨 Auto Detects OwO Warnings
 ⏱ Auto Cut After 1 Warning
 💎 Auto Determine Hit/Stand
 👓 Tracking & Profit Calculator
 🏹 Fast And Secure
 🧠 Smart Dynamic
 🎯 Integrated Data with Advanced Decisions

**__Made with 💖 and 🧠 by GhoSty | [Async Development]__** """
    await ctx.send(ghosty_help)

@ghosty.command()
async def bets(ctx, seq_name=None):
    cfg = load_config()
    if not seq_name:
        current = cfg.get("BET_SEQUENCE", "Low")
        return await ctx.send(f"⚙️ Usage: `.bets Low` or `.bets High` (High sequence not recommended)\nCurrent: {current}")
    target = seq_name.capitalize()
    if target not in BET_SEQUENCES:
        return await ctx.send("❌ Invalid sequence. Use `Low` or `High`.")
    cfg["BET_SEQUENCE"] = target
    with open("config.json", "w") as f:
        json.dump(cfg, f, indent=2)
    await ctx.send(f"✅ Sequence updated to **__{target}__**. Applies on win/restart.")

@ghosty.command()
async def status(ctx):
    global data
    balance = await fetch_owo_balance(ctx)
    if balance is not None:
        data["current_balance"] = balance
        save_data(data)
        print(f"{Fore.GREEN}[STATUS] Current balance updated: {balance:,}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}[STATUS] Could not fetch balance, using saved value{Style.RESET_ALL}")


    profit = data["current_balance"] - data["starting_balance"]
    profit_str = f"+{profit:,}" if profit >= 0 else f"{profit:,}"
    status_icon = "🟢" if profit >= 0 else "🔴"
    total_games = data["wins"] + data["losses"] + data["ties"]
    win_pct = (data["wins"] / total_games * 100) if total_games > 0 else 0.0
    loss_pct = (data["losses"] / total_games * 100) if total_games > 0 else 0.0
    start_dt = datetime.fromisoformat(data["start_timestamp"]) if data["start_timestamp"] else datetime.now()
    elapsed = datetime.now() - start_dt
    h, rem = divmod(int(elapsed.total_seconds()), 3600)
    m, s = divmod(rem, 60)


    cfg = load_config()
    text = (
        f"📊 **__GHOSTY OwO BLACKJACK FARM STATUS__**\n\n"
        f"{status_icon} Balance: Started **__{data['starting_balance']:,}__** | Current **__{data['current_balance']:,}__**\n"
        f"💸 Profit/Loss: **__{profit_str}__**\n\n"
        f"🎲 Results: Wins **__{data['wins']}__** ({win_pct:.1f}%) | Losses **__{data['losses']}__** ({loss_pct:.1f}%) | Ties **__{data['ties']}__**\n\n"
        f"⏱️ Runtime: Started **__{start_dt.strftime('%H:%M %m/%d')}__** | Elapsed **__{h}h {m}m {s}s__**\n\n"
        f"⚙️ Config: Sequence **__{cfg.get('BET_SEQUENCE', 'Low')}__** | Index **__{data.get('seq_index', 0)}__** | Commands **__{data['commands_used']}__**"
    )
    await ctx.send(text)

if __name__ == "__main__":
    config = load_config()
    if not os.path.exists("config.json") or not config.get("TOKEN"):
        print(f"{Fore.RED}❌ Missing config.json or TOKEN.{Style.RESET_ALL}")
        exit(1)
    print(
    f"""{Fore.BLUE}

           ▒▒                    ▒▒            ░░░░░░░░░░░  ░░░░░░░░░░░░░░░
        ▒▒▒▒▒▒▒   ▒▒▒     ▒▒▒▒ ▒▒▒▒▒▒▒▒      ░░░█████████░░░░█████████████░░
      ▒▒▒▒████▒▒ ▒▒█▒▒  ▒▒▒█▒▒▒▒░█████▒    ░░░████░░░░░░██░░░░░░░░░██░░░░░░
     ▒▒▒▒██░░██▒▒▒██▒▒ ▒▒░██▒░▒██░░░░█▒     ░░░░░█░░░░░░░██░░░░░░░░██░░░
     ▒▒██░░░░██▒▒██▒▒▒ ▒░██▒▒██░░░░░░█▒        ░░█░░░░░░░██░░░░░░░░██░░░
    ▒▒██░░█░░█▒▒▒█▒▒▒▒▒▒░█▒▒▒█░░░█░░██▒       ░░░█░░░░░░██░░░░░░░░░██░░░
    ▒▒█░░░░░░█▒▒█░░██░▒░█▒▒ ▒█░░░░░█▒▒▒       ░░██░░█████░░░░░░░░░░██░░░
    ▒▒█░░░░██▒▒▒████████▒▒  ▒██░░███▒▒        ░░█████████░░░░░░░░░███░░░
     ▒██████▒▒▒███▒▒▒██▒▒   ▒▒████▒▒▒         ░░█░░░░░░░██░░░░░░░░██░░░
    ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒     ▒▒▒▒▒▒          ░░██░░░░░░░██░░░█░░░░██░░░
     ▒▒▒▒▒    ▒▒▒▒▒▒▒▒▒      ▒▒▒▒▒        ░░░░░█░░░░░░░███░░░█░░░██░░░
               ▒▒   ▒▒        ▒▒         ░░███░█░░░░░███░░░░░█████░░░
                                          ░░░█████████░░░   ░░███░░░


                                                 Async Development Stable Build Version: 120426.2.0.0{Style.RESET_ALL}"""
    )
    print(f"{Fore.LIGHTRED_EX}\n\n > Made By GhoSty [Async Development]{Style.RESET_ALL}")
    ghosty.run(config["TOKEN"], bot=False)
