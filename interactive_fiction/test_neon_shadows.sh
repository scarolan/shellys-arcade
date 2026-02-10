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
