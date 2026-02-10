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
run_test "Ask Raven about tattoo after paying reveals backstory hint" \
    "take datapad\ndown\nnorth\npay raven\nask raven about tattoo\nquit\ny" \
    "reminder"
run_test "Ask Raven about tattoo before paying returns gatekeeping line" \
    "down\nnorth\nask raven about tattoo\nquit\ny" \
    "Info costs satoshis"
run_test "Tanaka is at precinct" "down\nwest\nlook\nquit\ny" "tanaka|detective"

# --- PUZZLE PROGRESSION ---
echo ""
echo "--- Puzzle Progression ---"
run_test "Can pay Raven for information" "take datapad\ndown\nnorth\npay raven\nquit\ny" "satoshis transfer"
run_test "Can give datapad to Zephyr" "take datapad\ndown\neast\nsouth\ngive datapad to zephyr\nquit\ny" "decrypt|keycard|zheng|harmon"
run_test "Keycard grants access to Zheng-Harmon" "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nshow keycard to guard\nuse keycard\nup\nquit\ny" "elevator|lobby|executive|floor"
run_test "Can find experiment logs via cyberspace" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nexamine logs\nquit\ny" "experiment|neural|clinic|7749"
run_test "Can find Lily at clinic" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nlook\nquit\ny" "lily|chen|daughter|machine"

# --- INSERT KEYCARD VARIANTS ---
echo ""
echo "--- Insert Keycard Variants ---"

# Base path to get keycard and reach executive floor
# take datapad, pay raven, give datapad to zephyr, use keycard at lobby, go up
INSERT_BASE="take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup"

run_test "insert keycard unlocks server room" \
    "${INSERT_BASE}\ninsert keycard\neast\nlook\nquit\ny" \
    "ACCESS GRANTED|server room|Server Room"

run_test "insert keycard in terminal unlocks server room" \
    "${INSERT_BASE}\ninsert keycard in terminal\neast\nlook\nquit\ny" \
    "ACCESS GRANTED|server room|Server Room"

run_test "insert keycard in slot unlocks server room" \
    "${INSERT_BASE}\ninsert keycard in slot\neast\nlook\nquit\ny" \
    "ACCESS GRANTED|server room|Server Room"

run_test "insert card in terminal unlocks server room" \
    "${INSERT_BASE}\ninsert card in terminal\neast\nlook\nquit\ny" \
    "ACCESS GRANTED|server room|Server Room"

run_test "use keycard still works" \
    "${INSERT_BASE}\nuse keycard\neast\nlook\nquit\ny" \
    "ACCESS GRANTED|server room|Server Room"

run_test "insert keycard when already unlocked shows already granted" \
    "${INSERT_BASE}\nuse keycard\ninsert keycard in terminal\nquit\ny" \
    "already shows ACCESS GRANTED|already"

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
run_test "Can hack through ICE" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nquit\ny" "shatters|exploit|vault is open"
run_test "Can reach data vault after hacking ICE" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\nlook\nquit\ny" "data vault|cathedral|data node"
run_test "Can extract data and return to server room" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nlook\nquit\ny" "server room|server racks"
run_test "Disconnect returns to server room" "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\ndisconnect\nlook\nquit\ny" "server room|server racks"
run_test "Server room shows ICE breached after hack and disconnect" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\ndisconnect\nlook\nquit\ny" \
    "breached the ICE.*jack in to access the data vault"
run_test "Enter vault reaches data vault after hacking ICE" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nenter vault\nlook\nquit\ny" \
    "data vault|cathedral|data node"
run_test "Enter data vault reaches data vault after hacking ICE" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nenter data vault\nlook\nquit\ny" \
    "data vault|cathedral|data node"
run_test "Enter vault blocked when ICE is still active" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nenter vault\nquit\ny" \
    "ICE blocks|intrusion countermeasures|hack"
run_test "Disconnect lily gives clean redirect" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ndisconnect lily\nquit\ny" \
    "free lily"
run_test "Disconnect lily does not expose internal token" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ndisconnect lily\nquit\ny" \
    "zdc" true

# --- ICE PUZZLE MULTI-STEP ---
echo ""
echo "--- ICE Puzzle Multi-Step ---"
run_test "Hack without scanning fails with hint to scan" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nquit\ny" \
    "scan the ICE|attacking blind"
run_test "Hack without scanning does not bypass ICE" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nhack\nnorth\nquit\ny" \
    "ICE blocks|intrusion countermeasures|hack"
run_test "Hack after scan ICE only fails with hint to scan streams" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nhack\nquit\ny" \
    "scan.*data streams|exploit|don't have an exploit"
run_test "Scan streams before scan ICE gives hint" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan streams\nquit\ny" \
    "scan the ICE|meaningless|what you're looking for"
run_test "Scan ICE reveals vulnerability" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nquit\ny" \
    "buffer overflow|hairline fracture|vulnerability"
run_test "Scan streams after scan ICE yields exploit" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nquit\ny" \
    "exploit sequence|payload|ready"

# --- POST-RESCUE NPC DIALOGUE ---
echo ""
echo "--- Post-Rescue NPC Dialogue ---"

# Full path to free Lily, then backtrack to ask Kai about lily
run_test "Ask Kai about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nup\nask kai about lily\nquit\ny" \
    "brought my daughter home|She's safe"

run_test "Ask Kai about lily after rescue does not show pre-rescue text" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nup\nask kai about lily\nquit\ny" \
    "stopped answering my calls" "true"

run_test "Ask Raven about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nnorth\nask raven about lily\nquit\ny" \
    "pulled the Chen girl out"

run_test "Ask Zephyr about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\neast\nsouth\nask zephyr about lily\nquit\ny" \
    "You got her out|breathing free air"

run_test "Ask Tanaka about lily after rescue shows new dialogue" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nsouth\nup\nwest\nask tanaka about lily\nquit\ny" \
    "found the Chen girl|pushed harder"

# --- POST-RESCUE RIG DESCRIPTION ---
echo ""
echo "--- Post-Rescue Rig Description ---"

run_test "Rig description after freeing Lily does not mention Lily is connected" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nexamine rig\nquit\ny" \
    "Lily is connected" "true"

run_test "Rig description after freeing Lily shows disconnected state" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nexamine rig\nquit\ny" \
    "dead and silent|disconnected cables"

run_test "Clinic room description after freeing Lily shows empty chair" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nlook\nquit\ny" \
    "reclined chair is empty"

# --- LILY ROOFTOP BEHAVIOR ---
echo ""
echo "--- Lily Rooftop Behavior ---"

run_test "Lily does not follow player to rooftop while Voss is alive" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nlook\nquit\ny" \
    "Voss and Lily|Lily and.*Voss" "true"

run_test "Lily follows player to rooftop after Voss is dead" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nshoot voss\nlook\nshoot voss\ndown\nup\nlook\nquit\ny" \
    "Lily Chen"

# --- LILY CONVERSATION ---
echo ""
echo "--- Lily Conversation ---"

# Talk to unconscious Lily (before freeing)
run_test "Talk to Lily while unconscious produces appropriate response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\ntalk to lily\nquit\ny" \
    "unconscious"

# Talk to Lily after freeing her
run_test "Talk to Lily after freeing produces contextual response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntalk to lily\nquit\ny" \
    "Voss|Director Voss|neural experiments"

run_test "Talk to Lily after freeing does not show generic fallback" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntalk to lily\nquit\ny" \
    "doesn't seem interested in talking" "true"

# Ask Lily about Voss
run_test "Ask Lily about Voss returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about voss\nquit\ny" \
    "monster|rooftop|experiment"

# Ask Lily about father/Kai
run_test "Ask Lily about father returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about father\nquit\ny" \
    "worried sick|coming home"

run_test "Ask Lily about kai returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about kai\nquit\ny" \
    "worried sick|coming home"

# Ask Lily about clinic/rig
run_test "Ask Lily about clinic returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about clinic\nquit\ny" \
    "rig|neural pathways|cyberspace prison"

run_test "Ask Lily about rig returns meaningful response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nask lily about rig\nquit\ny" \
    "rig|neural pathways|cyberspace prison"

# Ask unconscious Lily
run_test "Ask unconscious Lily produces appropriate response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nask lily about voss\nquit\ny" \
    "unconscious"

# Tell Lily about something
run_test "Tell Lily about something after freeing produces Lily-specific response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ntell lily about voss\nquit\ny" \
    "believe you|nothing surprises me"

# Give item to Lily
run_test "Give item to Lily after freeing produces Lily-specific response" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\ngive pistol to lily\nquit\ny" \
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
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nexamine logs\ndrop logs\ntake logs\nquit\ny" \
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
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nup\nexamine edge\nquit\ny" \
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
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nexamine gurneys\nquit\ny" \
    "overturned gurneys|shattered vials"
run_test "Clinic: examine chair returns description" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nexamine chair\nquit\ny" \
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
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\nexamine columns\nquit\ny" \
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
run_test "Full game is winnable (best ending - Lily lives)" \
    "take datapad\nopen desk\ntake all\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nshoot voss\nlook\nshoot voss\nquit\ny" \
    "congratulations|justice won|you won"

# --- BOSS FIGHT: MULTI-BEAT MECHANICS ---
echo ""
echo "--- Boss Fight: Multi-Beat Mechanics ---"

# Base path to reach rooftop with Lily freed
BOSS_BASE_LILY="take datapad\nopen desk\ntake all\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup"

# Base path to reach rooftop WITHOUT freeing Lily
BOSS_BASE_NO_LILY="take datapad\nopen desk\ntake all\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nup"

run_test "First shot does not kill Voss (multi-beat fight)" \
    "${BOSS_BASE_LILY}\nshoot voss\nlook\nquit\ny" \
    "Voss is backing toward the helicopter"

run_test "First shot wounds player (Voss fires back)" \
    "${BOSS_BASE_LILY}\nshoot voss\nquit\ny" \
    "white-hot pain|shoulder"

run_test "Helicopter/helipad is mentioned on rooftop" \
    "${BOSS_BASE_LILY}\nlook\nquit\ny" \
    "helicopter|helipad"

run_test "Can examine helicopter on rooftop" \
    "${BOSS_BASE_LILY}\nexamine helicopter\nquit\ny" \
    "corporate helicopter|escape route"

run_test "Can examine helipad on rooftop" \
    "${BOSS_BASE_LILY}\nexamine helipad\nquit\ny" \
    "painted circle|helicopter"

# --- BOSS FIGHT: ENDING A (BEST - LILY LIVES) ---
echo ""
echo "--- Boss Fight: Ending A (Best - Lily Lives) ---"

run_test "Ending A: Lily distracts Voss after waiting" \
    "${BOSS_BASE_LILY}\nshoot voss\nlook\nquit\ny" \
    "Lily steps forward|Director Voss|I remember ALL of it"

run_test "Ending A: Clean kill when Lily distracts" \
    "${BOSS_BASE_LILY}\nshoot voss\nlook\nshoot voss\nquit\ny" \
    "clear shot|congratulations|justice won|you won"

run_test "Ending A: Score is 120 (max)" \
    "${BOSS_BASE_LILY}\nshoot voss\nlook\nshoot voss\nquit\ny" \
    "120 out of a possible 120"

# --- BOSS FIGHT: ENDING B (BITTERSWEET - LILY SACRIFICED) ---
echo ""
echo "--- Boss Fight: Ending B (Bittersweet - Lily Sacrificed) ---"

run_test "Ending B: Shooting immediately with Lily causes sacrifice" \
    "${BOSS_BASE_LILY}\nshoot voss\nshoot voss\nquit\ny" \
    "thrown herself forward|bullet catches her"

run_test "Ending B: Voss dies in sacrifice ending" \
    "${BOSS_BASE_LILY}\nshoot voss\nshoot voss\nquit\ny" \
    "Voss square in the throat|puppet with cut strings"

run_test "Ending B: Lily dies in sacrifice ending" \
    "${BOSS_BASE_LILY}\nshoot voss\nshoot voss\nquit\ny" \
    "Tell my father|cost was too high|Lily Chen is dead"

run_test "Ending B: Score is 110 (not max)" \
    "${BOSS_BASE_LILY}\nshoot voss\nshoot voss\nquit\ny" \
    "110 out of a possible 120"

# --- BOSS FIGHT: ENDING C (VOSS ESCAPES) ---
echo ""
echo "--- Boss Fight: Ending C (Voss Escapes) ---"

run_test "Ending C (no Lily): Voss escapes after delay" \
    "${BOSS_BASE_NO_LILY}\nshoot voss\nlook\nlook\nlook\nquit\ny" \
    "helicopter lifts off|disappears into the storm|partial victory"

run_test "Ending C (with Lily): Voss escapes after delay at phase 2" \
    "${BOSS_BASE_LILY}\nshoot voss\nlook\nlook\nlook\nlook\nquit\ny" \
    "shoves Lily aside|sprints for the helicopter|evidence"

run_test "Ending C: Voss escape ending still triggers victory (deadflag 2)" \
    "${BOSS_BASE_NO_LILY}\nshoot voss\nlook\nlook\nlook\nquit\ny" \
    "85 out of a possible 120"

# --- BOSS FIGHT: KILL WITHOUT LILY ---
echo ""
echo "--- Boss Fight: Kill Without Lily ---"

run_test "Can kill Voss without Lily (second shot in phase 1)" \
    "${BOSS_BASE_NO_LILY}\nshoot voss\nshoot voss\nquit\ny" \
    "shot takes Voss in the chest|crumples to the ground"

run_test "Killing Voss without Lily then freeing Lily wins the game" \
    "${BOSS_BASE_NO_LILY}\nshoot voss\nshoot voss\ndown\nfree lily\nquit\ny" \
    "congratulations|rescued Lily|Voss is dead|victory"

run_test "Kill without Lily path achieves max score" \
    "${BOSS_BASE_NO_LILY}\nshoot voss\nshoot voss\ndown\nfree lily\nquit\ny" \
    "120 out of a possible 120"

# --- QA IMPROVEMENTS (Issue #63) ---
echo ""
echo "--- QA Improvements ---"

# 1. Redundant intro text removed
run_test "Intro does not mention 'latest client is waiting'" \
    "look\nquit\ny" \
    "latest client is waiting" "true"

# 2. Bar examinable objects
run_test "Bar: examine ads returns description" \
    "down\nnorth\nexamine ads\nquit\ny" \
    "holographic ads|no longer exist|projectors"

run_test "Bar: examine woman returns description" \
    "down\nnorth\nexamine woman\nquit\ny" \
    "grinning|Wintermute|gin|Forget What You Know"

run_test "Bar: examine gin returns description" \
    "down\nnorth\nexamine gin\nquit\ny" \
    "grinning|Wintermute|gin"

run_test "Bar: examine bottle returns description in bar" \
    "down\nnorth\nexamine bottle\nquit\ny" \
    "grinning|Wintermute|gin"

run_test "Bar: examine ads does not show 'no such thing'" \
    "down\nnorth\nexamine ads\nquit\ny" \
    "no such thing" "true"

run_test "Bar: examine woman does not show 'no such thing'" \
    "down\nnorth\nexamine woman\nquit\ny" \
    "no such thing" "true"

# 3. Raven initial property
run_test "Raven has vivid listing text instead of generic" \
    "down\nnorth\nlook\nquit\ny" \
    "polishes a glass|cybernetic left eye|calculating"

run_test "Raven listing does not show generic 'You can see Raven here'" \
    "down\nnorth\nlook\nquit\ny" \
    "You can see Raven here" "true"

# 4. Atmospheric bar NPCs
run_test "Bar: VR junkies are present" \
    "down\nnorth\nlook\nquit\ny" \
    "VR junkies|headsets"

run_test "Bar: examine junkies returns description" \
    "down\nnorth\nexamine junkies\nquit\ny" \
    "VR junkies|knock-off|simulation"

run_test "Bar: street worker is present" \
    "down\nnorth\nlook\nquit\ny" \
    "street worker|synthleather"

run_test "Bar: examine street worker returns description" \
    "down\nnorth\nexamine street worker\nquit\ny" \
    "synthleather|circuit-pattern|tattoos"

run_test "Bar: dealer is present" \
    "down\nnorth\nlook\nquit\ny" \
    "gaunt man|darkest corner"

run_test "Bar: examine dealer returns description" \
    "down\nnorth\nexamine dealer\nquit\ny" \
    "gaunt man|long coat|stim patches"

# 5. Snarky robot in Zephyr's Den
run_test "Den: Bolt robot is present" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nlook\nquit\ny" \
    "ZB-7|robot|Bolt"

run_test "Den: talk to robot gives snarky response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ntalk to robot\nquit\ny" \
    "cable organizer|thrilling|fascinating"

run_test "Den: ask robot about zephyr gives snarky response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nask robot about zephyr\nquit\ny" \
    "so-called owner|sorting patch cables|labor complaint"

run_test "Den: examine bolt returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nexamine bolt\nquit\ny" \
    "dented robot|optical sensor|ZB-7|BOLT"

# 6. Zephyr gate and keycard confirmation
run_test "Zephyr mentions owing Raven a favor" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nquit\ny" \
    "owe Raven a favor"

run_test "Keycard handoff shows explicit confirmation" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nquit\ny" \
    "You now have the keycard|slides a platinum keycard"

# 7. Rooftop trap during Voss confrontation
run_test "Cannot leave rooftop during Voss fight" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\nwest\ndown\nnorth\ndown\nnorth\nfree lily\nup\nshoot voss\ndown\nquit\ny" \
    "not going anywhere|fires a shot"

# --- ADDITIONAL SCENERY: ALLEY ---
echo ""
echo "--- Additional Scenery: Alley ---"

run_test "Alley: examine cat returns description" \
    "down\neast\nexamine cat\nquit\ny" \
    "scraggly grey cat|yellow eyes"

run_test "Alley: examine box returns description" \
    "down\neast\nexamine box\nquit\ny" \
    "soggy cardboard box|food wrappers"

run_test "Alley: examine signage returns description" \
    "down\neast\nexamine signage\nquit\ny" \
    "Mandarin signage|augmentation clinics|AKIRA LIVES"

run_test "Alley: examine fire escape returns description" \
    "down\neast\nexamine fire escape\nquit\ny" \
    "rusty fire escape|metal groaning"

# --- ADDITIONAL SCENERY: INDUSTRIAL DISTRICT ---
echo ""
echo "--- Additional Scenery: Industrial District ---"

run_test "Industrial: examine dumpster returns description" \
    "down\ndown\nexamine dumpster\nquit\ny" \
    "rusted-out industrial dumpster|chemical waste"

run_test "Industrial: examine sign returns description" \
    "down\ndown\nexamine sign\nquit\ny" \
    "NeoMed Solutions|went under years ago"

run_test "Industrial: examine door returns description" \
    "down\ndown\nexamine door\nquit\ny" \
    "keypad requires a 4-digit code"

# --- ADDITIONAL SCENERY: BAR ---
echo ""
echo "--- Additional Scenery: Bar ---"

run_test "Bar: examine neon tubes returns description" \
    "down\nnorth\nexamine neon tubes\nquit\ny" \
    "neon tubes|unsteady glow|buzzing"

run_test "Bar: examine stools returns description" \
    "down\nnorth\nexamine stools\nquit\ny" \
    "bar stools|cracked vinyl|bolted to the floor"

# --- ADDITIONAL SCENERY: PRECINCT ---
echo ""
echo "--- Additional Scenery: Precinct ---"

run_test "Precinct: examine bulletin board returns description" \
    "down\nwest\nexamine bulletin board\nquit\ny" \
    "bulletin board|wanted posters|missing persons"

# --- ADDITIONAL SCENERY: DEN ---
echo ""
echo "--- Additional Scenery: Den ---"

run_test "Den: examine keyboard returns description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nexamine keyboard\nquit\ny" \
    "holographic keyboard|blue keys"

# --- ADDITIONAL SCENERY: ROOFTOP ---
echo ""
echo "--- Additional Scenery: Rooftop ---"

run_test "Rooftop: examine skyline returns description" \
    "${BOSS_BASE_LILY}\nexamine skyline\nquit\ny" \
    "rain|neon|lightning"

run_test "Rooftop: examine wind returns description" \
    "${BOSS_BASE_LILY}\nexamine wind\nquit\ny" \
    "howls|rain"

# --- HELP SYSTEM ---
echo ""
echo "--- Help System ---"

run_test "Help command shows PI field manual" \
    "help\nquit\ny" \
    "KIRA VEX.*PI FIELD MANUAL|NAVIGATION PROTOCOLS|INVESTIGATION OPS"

run_test "Help command lists special actions" \
    "help\nquit\ny" \
    "shoot.*Last resort|jack in.*neural jack|scan.*cyberspace"

# --- CYBERSPACE RE-ENTRY ---
echo ""
echo "--- Cyberspace Re-entry ---"

run_test "Cannot jack in after data extraction" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\njack in\nscan ice\nscan streams\nhack\nnorth\ntake node\njack in\nquit\ny" \
    "already extracted"

run_test "Disconnect outside cyberspace gives clean message" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\ndisconnect\nquit\ny" \
    "not jacked into anything"

# --- GUARD NPC ---
echo ""
echo "--- Guard NPC ---"

run_test "Show keycard to guard grants access" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nshow keycard to guard\nquit\ny" \
    "examines your keycard|steps aside"

run_test "Guard dismisses questions" \
    "down\nsouth\nask guard about voss\nquit\ny" \
    "Move along"

# --- BOLT ROBOT CONVERSATION ---
echo ""
echo "--- Bolt Robot Conversation ---"

run_test "Ask Bolt about raven gives snarky response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nask robot about raven\nquit\ny" \
    "firmware update|attitude problem"

run_test "Ask Bolt about zheng gives snarky response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nask robot about zheng\nquit\ny" \
    "megacorp|disposable hardware"

run_test "Ask Bolt about itself gives snarky response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\nask robot about bolt\nquit\ny" \
    "Model ZB-7|cable management|withering commentary"

# --- DRINK VERB ---
echo ""
echo "--- Drink Verb ---"

run_test "Drink whiskey bottle gives thematic response" \
    "take bottle\ndrink bottle\nquit\ny" \
    "Deckard's Reserve"

run_test "Drink whiskey bottle does not give library default" \
    "take bottle\ndrink bottle\nquit\ny" \
    "nothing suitable to drink" \
    true

run_test "Drink decanter on executive floor gives thematic response" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\ndrink decanter\nquit\ny" \
    "whiskey|liquor cabinet|case can't"

run_test "Drink decanter does not give library default" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\ndrink decanter\nquit\ny" \
    "nothing suitable to drink" \
    true

# --- RAVEN GIVE BUG (Issue #70) - FIXED ---
echo ""
echo "--- Raven Give Bug (Fixed) ---"

# Fixed: giving items to Raven now rejects with flavour text, no payment triggered.
run_test "Give bottle to Raven rejects with flavour text (fix #70)" \
    "take datapad\ntake bottle\ndown\nnorth\ngive bottle to raven\nquit\ny" \
    "deal in satoshis"

run_test "Give pistol to Raven rejects with flavour text (fix #70)" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\ngive pistol to raven\nquit\ny" \
    "deal in satoshis"

run_test "Give bottle to Raven does not trigger payment (fix #70)" \
    "take datapad\ntake bottle\ndown\nnorth\ngive bottle to raven\nquit\ny" \
    "satoshis transfer" "true"

run_test "Give pistol to Raven does not trigger payment (fix #70)" \
    "take datapad\nopen desk\ntake pistol\ndown\nnorth\ngive pistol to raven\nquit\ny" \
    "satoshis transfer" "true"

# --- MISSING SCENERY: KNOWN BUGS ---
echo ""
echo "--- Missing Scenery: Known Bugs ---"

# These document missing scenery objects (issues #65, #66, #71, #72).
# After fixes, these tests should be inverted (the "no such thing" should disappear).
run_test "Street: examine sign describes noodle sign" \
    "down\nexamine sign\nquit\ny" \
    "Hiro's Noodles"

run_test "Alley: examine laundry shows cant see (known bug #65)" \
    "down\neast\nexamine laundry\nquit\ny" \
    "can't see any such thing"

run_test "Precinct: examine lights shows cant see (known bug #66)" \
    "down\nwest\nexamine lights\nquit\ny" \
    "can't see any such thing"

run_test "Server: examine fans shows description" \
    "take datapad\ndown\nnorth\npay raven\nsouth\neast\nsouth\ngive datapad to zephyr\nnorth\nwest\nsouth\nuse keycard\nup\nuse keycard\neast\nexamine fans\nquit\ny" \
    "cooling fans"

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
