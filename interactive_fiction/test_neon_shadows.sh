#!/bin/bash
# Test harness for Neon Shadows interactive fiction game
# Uses dfrotz to pipe commands and check output

GAME="neon_shadows.z5"
SOURCE="neon_shadows.inf"
LIB="/usr/local/share/inform6/lib/"
PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

run_test() {
    local test_name="$1"
    local commands="$2"
    local expected="$3"
    local negate="${4:-false}"

    TOTAL=$((TOTAL + 1))

    output=$(echo -e "$commands" | /usr/games/dfrotz -m -p -w 999 -Z 0 "$GAME" 2>/dev/null)

    if [ "$negate" = "true" ]; then
        if echo "$output" | grep -qiE "$expected"; then
            FAIL=$((FAIL + 1))
            echo -e "${RED}FAIL${NC}: $test_name (found '$expected' but shouldn't have)"
            return 1
        else
            PASS=$((PASS + 1))
            echo -e "${GREEN}PASS${NC}: $test_name"
            return 0
        fi
    else
        if echo "$output" | grep -qiE "$expected"; then
            PASS=$((PASS + 1))
            echo -e "${GREEN}PASS${NC}: $test_name"
            return 0
        else
            FAIL=$((FAIL + 1))
            echo -e "${RED}FAIL${NC}: $test_name"
            echo "  Expected to find: $expected"
            echo "  Got output (last 20 lines):"
            echo "$output" | tail -20 | sed 's/^/    /'
            return 1
        fi
    fi
}

echo "=== Neon Shadows Test Suite ==="
echo ""

# --- COMPILATION TEST ---
echo "--- Compilation ---"
TOTAL=$((TOTAL + 1))
compile_output=$(inform6 +${LIB} "$SOURCE" "$GAME" 2>&1)
if [ $? -eq 0 ]; then
    PASS=$((PASS + 1))
    echo -e "${GREEN}PASS${NC}: Game compiles without errors"
else
    FAIL=$((FAIL + 1))
    echo -e "${RED}FAIL${NC}: Compilation failed"
    echo "$compile_output"
    echo ""
    echo "=== Cannot continue without compilation. Fix errors first. ==="
    exit 1
fi

# --- GAME START TESTS ---
echo ""
echo "--- Game Start ---"
run_test "Game loads and shows opening text" "look\nquit\ny" "office|Kira|Neo-Angeles|neon"
run_test "Starting room is Your Office" "look\nquit\ny" "office"
run_test "Opening mentions cyberpunk/noir elements" "look\nquit\ny" "neon|rain|city|street"

# --- ROOM NAVIGATION ---
echo ""
echo "--- Room Navigation ---"
run_test "Can go to street from office" "down\nlook\nquit\ny" "street|rain|neon"
run_test "Can reach Neon Lotus Bar" "down\nnorth\nlook\nquit\ny" "bar|lotus|neon"
run_test "Bar has bartender/Raven" "down\nnorth\nlook\nquit\ny" "raven|bartender"
run_test "Can reach Chinatown/alley area" "down\neast\nlook\nquit\ny" "alley|chinatown|narrow"
run_test "Can reach Police Precinct" "down\nwest\nlook\nquit\ny" "precinct|police|station"

# --- OBJECT INTERACTION ---
echo ""
echo "--- Object Interaction ---"
run_test "Can see datapad in office" "look\nquit\ny" "datapad|data pad"
run_test "Can take datapad" "take datapad\ninventory\nquit\ny" "datapad|data pad"
run_test "Credits are not a takeable object" "open desk\ntake satoshis\ninventory\nquit\ny" "satoshis|cred-sticks" "true"
run_test "Can take pistol" "open desk\ntake pistol\ntake gun\ninventory\nquit\ny" "pistol|gun"
run_test "Inventory shows no satoshis" "take all\ninventory\nquit\ny" "satoshis|cred-sticks" "true"
run_test "Can examine objects" "examine datapad\nquit\ny" "encrypt|data|lily|neural"

# --- NPC INTERACTION ---
echo ""
echo "--- NPC Interaction ---"
run_test "Kai Chen is in the office at start" "look\nquit\ny" "kai|chen|client|father"
run_test "Can talk to Kai Chen" "talk to kai\nask kai about lily\nquit\ny" "daughter|lily|missing|find"
run_test "Raven responds to conversation" "down\nnorth\ntalk to raven\nask raven about zheng\nquit\ny" "raven|know|info|zheng|corp"
run_test "Tanaka is at precinct" "down\nwest\nlook\nquit\ny" "tanaka|detective"

# --- PUZZLE PROGRESSION ---
echo ""
echo "--- Puzzle Progression ---"
run_test "Can pay Raven for information" "take datapad\ndown\nnorth\npay raven\nquit\ny" "satoshis transfer"
run_test "Can give datapad to Zephyr" "take datapad\ndown\neast\nsouth\ngive datapad to zephyr\nquit\ny" "decrypt|keycard|zheng|harmon"
run_test "Keycard grants access to Zheng-Harmon" "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nshow keycard to guard\nuse keycard\nup\nquit\ny" "elevator|lobby|executive|floor"
run_test "Can find experiment logs via cyberspace" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nexamine logs\nquit\ny" "experiment|neural|clinic|7749"
run_test "Can find Lily at clinic" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nlook\nquit\ny" "lily|chen|daughter|machine"

# --- BLOCKING/GATES ---
echo ""
echo "--- Blocking/Gates ---"
run_test "Cannot enter Zheng-Harmon without keycard" "down\nsouth\nenter\nup\nquit\ny" "security|guard|block|keycard|stop|can't"
run_test "Cannot enter server room without using keycard on terminal" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\neast\nquit\ny" "reinforced door|security terminal|access code"
run_test "Zephyr's den requires knowing about it" "down\neast\nsouth\nquit\ny" "hidden|door|can't|locked|wall|nothing"
run_test "Cannot take logs directly from server room" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\ntake logs\nquit\ny" "locked behind|military-grade ICE|jack"
run_test "Jack in fails outside server room" "jack in\nquit\ny" "no neural interface"
run_test "ICE blocks vault before hacking" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nnorth\nquit\ny" "ICE blocks|intrusion countermeasures|hack"
run_test "Nonsense input doesn't crash" "xyzzy\nfrobnicate\nquit\ny" "understand|don't know|error|what|recognise|verb"

# --- CYBERSPACE ---
echo ""
echo "--- Cyberspace ---"
run_test "Can jack into server and enter cyberspace" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nlook\nquit\ny" "cyberspace|nexus|ICE|vault|digital"
run_test "Can hack through ICE" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nquit\ny" "shatters|buffer overflow|vault is open"
run_test "Can reach data vault after hacking ICE" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\nlook\nquit\ny" "data vault|cathedral|data node"
run_test "Can extract data and return to server room" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nlook\nquit\ny" "server room|server racks"
run_test "Disconnect returns to server room" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\ndisconnect\nlook\nquit\ny" "server room|server racks"
run_test "Disconnect lily gives clean redirect" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ndisconnect lily\nquit\ny" \
    "free lily"
run_test "Disconnect lily does not expose internal token" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ndisconnect lily\nquit\ny" \
    "zdc" true

# --- POST-RESCUE NPC DIALOGUE ---
echo ""
echo "--- Post-Rescue NPC Dialogue ---"

# Full path to free Lily, then backtrack to ask Kai about lily
run_test "Ask Kai about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nup\nask kai about lily\nquit\ny" \
    "brought my daughter home|She's safe"

run_test "Ask Kai about lily after rescue does not show pre-rescue text" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nup\nask kai about lily\nquit\ny" \
    "stopped answering my calls" "true"

run_test "Ask Raven about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nnorth\nask raven about lily\nquit\ny" \
    "pulled the Chen girl out"

run_test "Ask Zephyr about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\neast\nsouth\nask zephyr about lily\nquit\ny" \
    "You got her out|breathing free air"

run_test "Ask Tanaka about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nwest\nask tanaka about lily\nquit\ny" \
    "found the Chen girl|pushed harder"

# --- POST-RESCUE RIG DESCRIPTION ---
echo ""
echo "--- Post-Rescue Rig Description ---"

run_test "Rig description after freeing Lily does not mention Lily is connected" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nexamine rig\nquit\ny" \
    "Lily is connected" "true"

run_test "Rig description after freeing Lily shows disconnected state" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nexamine rig\nquit\ny" \
    "dead and silent|disconnected cables"

run_test "Clinic room description after freeing Lily shows empty chair" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nlook\nquit\ny" \
    "reclined chair is empty"

# --- LILY ROOFTOP BEHAVIOR ---
echo ""
echo "--- Lily Rooftop Behavior ---"

run_test "Lily does not follow player to rooftop while Voss is alive" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nlook\nquit\ny" \
    "Voss and Lily|Lily and.*Voss" "true"

run_test "Lily follows player to rooftop after Voss is dead" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nshoot voss\ndown\nup\nlook\nquit\ny" \
    "Lily Chen"

# --- LILY CONVERSATION ---
echo ""
echo "--- Lily Conversation ---"

# Talk to unconscious Lily (before freeing)
run_test "Talk to Lily while unconscious produces appropriate response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ntalk to lily\nquit\ny" \
    "unconscious"

# Talk to Lily after freeing her
run_test "Talk to Lily after freeing produces contextual response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntalk to lily\nquit\ny" \
    "Voss|Director Voss|neural experiments"

run_test "Talk to Lily after freeing does not show generic fallback" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntalk to lily\nquit\ny" \
    "doesn't seem interested in talking" "true"

# Ask Lily about Voss
run_test "Ask Lily about Voss returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about voss\nquit\ny" \
    "monster|rooftop|experiment"

# Ask Lily about father/Kai
run_test "Ask Lily about father returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about father\nquit\ny" \
    "worried sick|coming home"

run_test "Ask Lily about kai returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about kai\nquit\ny" \
    "worried sick|coming home"

# Ask Lily about clinic/rig
run_test "Ask Lily about clinic returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about clinic\nquit\ny" \
    "rig|neural pathways|cyberspace prison"

run_test "Ask Lily about rig returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about rig\nquit\ny" \
    "rig|neural pathways|cyberspace prison"

# Ask unconscious Lily
run_test "Ask unconscious Lily produces appropriate response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nask lily about voss\nquit\ny" \
    "unconscious"

# Tell Lily about something
run_test "Tell Lily about something after freeing produces Lily-specific response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntell lily about voss\nquit\ny" \
    "believe you|nothing surprises me"

# Give item to Lily
run_test "Give item to Lily after freeing produces Lily-specific response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ngive pistol to lily\nquit\ny" \
    "Hold onto that|need it more"

# --- GRAMMAR: PLURAL OBJECTS ---
echo ""
echo "--- Grammar: Plural Objects ---"

run_test "Filing cabinets does not produce 'a filing cabinets'" \
    "examine cabinets\ntake cabinets\nquit\ny" \
    "a filing cabinets" "true"

run_test "Data streams does not produce 'a data streams'" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nexamine streams\ntake streams\nquit\ny" \
    "a data streams" "true"

run_test "Experiment logs does not produce 'a experiment logs'" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nexamine logs\ndrop logs\ntake logs\nquit\ny" \
    "a experiment logs" "true"

# --- SCENERY OBJECTS ---
echo ""
echo "--- Scenery Objects ---"

# Street scenery
run_test "Street: examine drone returns description" \
    "down\nexamine drone\nquit\ny" \
    "surveillance drone|spotlight"
run_test "Street: examine neon lights returns description" \
    "down\nexamine neon lights\nquit\ny" \
    "holographic advertisements|neon glow"
run_test "Street: examine rain returns description" \
    "down\nexamine rain\nquit\ny" \
    "hasn't stopped|pools in the cracks"

# Bar scenery
run_test "Bar: examine counter returns description" \
    "down\nnorth\nexamine counter\nquit\ny" \
    "scarred with cigarette|glass rings"
run_test "Bar: examine speaker returns description" \
    "down\nnorth\nexamine speaker\nquit\ny" \
    "jazz synth|saxophone"
run_test "Bar: examine regulars returns description" \
    "down\nnorth\nexamine regulars\nquit\ny" \
    "hollow-eyed|nurse their drinks"

# Den scenery (need to unlock path first)
run_test "Den: examine screens returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nexamine screens\nquit\ny" \
    "cascading code|surveillance feeds"
run_test "Den: examine cables returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nexamine cables\nquit\ny" \
    "tangled cables|copper veins"

# Alley scenery
run_test "Alley: examine wok stall returns description" \
    "down\neast\nexamine wok\nquit\ny" \
    "automated wok stall|synthetic noodles"
run_test "Alley: examine steam returns description" \
    "down\neast\nexamine steam\nquit\ny" \
    "rises from grates|chemical runoff"

# Lobby scenery
run_test "Lobby: examine logo returns description" \
    "down\nsouth\nexamine logo\nquit\ny" \
    "holographic logo|Innovation Through Integration"
run_test "Lobby: examine reception desk returns description" \
    "down\nsouth\nexamine reception\nquit\ny" \
    "curved reception desk|polished white"

# Executive floor scenery (need keycard)
run_test "Executive: examine desk returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nexamine desk\nquit\ny" \
    "genuine hardwood|polished to a mirror"
run_test "Executive: examine window returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nexamine window\nquit\ny" \
    "panoramic view|neon skyline"

# Rooftop scenery (need full game progression)
run_test "Rooftop: examine edge returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nup\nexamine edge\nquit\ny" \
    "dizzying void|long way down"

# Precinct scenery
run_test "Precinct: examine desks returns description" \
    "down\nwest\nexamine desks\nquit\ny" \
    "budget cuts|cold case files"
run_test "Precinct: examine coffee returns description" \
    "down\nwest\nexamine coffee\nquit\ny" \
    "cold coffee|oil floating"

# Clinic scenery (need logs for access)
run_test "Clinic: examine gurneys returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nexamine gurneys\nquit\ny" \
    "overturned gurneys|shattered vials"
run_test "Clinic: examine chair returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nexamine chair\nquit\ny" \
    "reclining chair|electrode pads"

# Server room scenery
run_test "Server: examine racks returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\nexamine racks\nquit\ny" \
    "humming server racks|blinking hardware"
run_test "Server: examine leds returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\nexamine leds\nquit\ny" \
    "rhythmic patterns|heartbeats"

# Cyberspace scenery
run_test "Cyberspace: examine structures returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nexamine structures\nquit\ny" \
    "crystalline structures|file directories"

# Data vault scenery
run_test "Data vault: examine columns returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\nexamine columns\nquit\ny" \
    "encrypted data|pillars"

# Industrial district scenery
run_test "Industrial: examine factories returns description" \
    "down\ndown\nexamine factories\nquit\ny" \
    "bones of dead giants|smokestacks"
run_test "Industrial: examine conveyor returns description" \
    "down\ndown\nexamine conveyor\nquit\ny" \
    "rust in the rain|circuit boards"

# Street scenery: no such thing check
run_test "Street: examine drone does not show 'no such thing'" \
    "down\nexamine drone\nquit\ny" \
    "no such thing" "true"

# --- GAME COMPLETION ---
echo ""
echo "--- Game Completion ---"
run_test "Full game is winnable" \
    "take datapad\nopen desk\ntake all\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nshoot voss\nquit\ny" \
    "free|saved|rescue|congratulations|end|won|victory"

# --- SUMMARY ---
echo ""
echo "========================="
echo "Results: $PASS passed, $FAIL failed, $TOTAL total"
echo "========================="

if [ $FAIL -gt 0 ]; then
    exit 1
else
    echo "All tests passed!"
    exit 0
fi
