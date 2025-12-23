#!/bin/bash

GREEN=$(tput setaf 2)
CYAN=$(tput setaf 6)
YELLOW=$(tput setaf 3)
MAGENTA=$(tput setaf 5)
RED=$(tput setaf 1)
BLUE=$(tput setaf 4)
WHITE=$(tput setaf 7)
BOLD=$(tput bold)
RESET=$(tput sgr0)

USE_DEFAULTS=false
BASE_URL="http://localhost:8000"
ENDPOINT=""
SESSION_ID=""
USER_ID=""

# === UTILITY FUNCTIONS ===

cleanup() {
    tput cnorm
    exit 0
}

show_help() {
    echo -e "${BOLD}${BLUE}AG-UI Streaming Chat${RESET}"
    echo -e "${YELLOW}Usage: $0 --endpoint=NAME [OPTIONS]${RESET}"
    echo -e "\n${YELLOW}Required:${RESET}"
    echo -e "  ${GREEN}--endpoint=NAME${RESET}       Endpoint to chat with (e.g., stream-forecasting)"
    echo -e "\n${YELLOW}Options:${RESET}"
    echo -e "  ${GREEN}--session-id=ID${RESET}       Session ID for memory persistence"
    echo -e "  ${GREEN}--user-id=ID${RESET}          User ID"
    echo -e "  ${GREEN}--url=URL${RESET}             Base URL (default: localhost:8000)"
    echo -e "  ${GREEN}--default${RESET}             Use default settings (skip prompts)"
    echo -e "  ${GREEN}--help, -h${RESET}            Show this help"
    echo -e "\n${YELLOW}Examples:${RESET}"
    echo -e "  ${CYAN}$0 --endpoint=stream-forecasting${RESET}"
    echo -e "  ${CYAN}$0 --endpoint=stream-forecasting --default${RESET}"
    echo -e "  ${CYAN}$0 --endpoint=stream-forecasting --session-id=my-session${RESET}"
    exit 0
}

# === API HELPERS ===

make_streaming_request() {
    local message="$1"
    
    local request_body=$(cat <<EOF
{
  "input": "$message",
  "session_id": "$SESSION_ID",
  "user_id": "$USER_ID",
  "stream_agui": true
}
EOF
)

    curl -s --no-buffer -X POST "$BASE_URL/$ENDPOINT" \
        -H 'Content-Type: application/json' \
        -H 'Accept: text/event-stream' \
        -d "$request_body"
}

# === RESPONSE PROCESSING ===

process_streaming_response() {
    local message="$1"

    echo -e "\n${WHITE}${BOLD}You:${RESET} ${message}\n"

    local start_time=$(date +%s.%N)
    local in_text_stream=false
    local first_message=true
    local tool_call_active=false
    local current_tool_name=""
    local tool_args_buffer=""

    make_streaming_request "$message" | while IFS= read -r raw_line; do
        if [[ "$raw_line" == data:* ]]; then
            local line="${raw_line#data: }"
        else
            local line="$raw_line"
        fi

        if [ -n "$line" ] && [ "$line" != "" ]; then
            if echo "$line" | jq -e . >/dev/null 2>&1; then
                local event_type=$(echo "$line" | jq -r '.type // "unknown"')
                
                case "$event_type" in
                    "RUN_STARTED")
                        local run_id=$(echo "$line" | jq -r '.runId // "unknown"')
                        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
                        echo -e "${BLUE}│${RESET} ${WHITE}${BOLD}Run Started${RESET}"
                        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
                        ;;

                    "TEXT_MESSAGE_START")
                        in_text_stream=true
                        if [ "$first_message" = true ]; then
                            echo -e "${GREEN}${BOLD}💬 Assistant:${RESET}"
                            first_message=false
                        fi
                        ;;

                    "TEXT_MESSAGE_CONTENT")
                        if [ "$in_text_stream" = true ]; then
                            local delta=$(echo "$line" | jq -r '.delta // ""')
                            if [ "$tool_call_active" = true ]; then
                                echo -e "\n"
                                tool_call_active=false
                            fi
                            printf "${WHITE}%s${RESET}" "$delta"
                        fi
                        ;;

                    "TEXT_MESSAGE_END")
                        if [ "$in_text_stream" = true ]; then
                            echo -e "\n"
                            in_text_stream=false
                        fi
                        ;;

                    "TOOL_CALL_START")
                        tool_call_active=true
                        current_tool_name=$(echo "$line" | jq -r '.toolCallName // "unknown"')
                        tool_args_buffer=""
                        echo -e "\n${YELLOW}┌─────────────────────────────────────────────────┐${RESET}"
                        echo -e "${YELLOW}│${RESET} ${MAGENTA}${BOLD}🔧 Tool Call:${RESET} ${WHITE}${current_tool_name}${RESET}"
                        echo -e "${YELLOW}├─────────────────────────────────────────────────┤${RESET}"
                        printf "${YELLOW}│${RESET} ${CYAN}Args:${RESET} "
                        ;;

                    "TOOL_CALL_ARGS")
                        local args_delta=$(echo "$line" | jq -r '.delta // ""')
                        tool_args_buffer="${tool_args_buffer}${args_delta}"
                        printf "${WHITE}%s${RESET}" "$args_delta"
                        ;;

                    "TOOL_CALL_RESULT")
                        local result=$(echo "$line" | jq -r '.content // "No result"')
                        echo -e "\n${YELLOW}│${RESET} ${GREEN}Result:${RESET} ${WHITE}${result}${RESET}"
                        ;;

                    "TOOL_CALL_END")
                        echo -e "${YELLOW}└─────────────────────────────────────────────────┘${RESET}\n"
                        current_tool_name=""
                        tool_args_buffer=""
                        ;;

                    "RUN_FINISHED")
                        local has_result=$(echo "$line" | jq -e '.result' >/dev/null 2>&1 && echo "true" || echo "false")
                        
                        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
                        echo -e "${BLUE}│${RESET} ${GREEN}${BOLD}✅ Run Finished${RESET}"
                        
                        if [ "$has_result" = "true" ]; then
                            local result_json=$(echo "$line" | jq -r '.result')
                            if [ "$result_json" != "null" ] && [ -n "$result_json" ]; then
                                echo -e "${BLUE}├─────────────────────────────────────────────────┤${RESET}"
                                echo -e "${BLUE}│${RESET} ${MAGENTA}${BOLD}📊 Structured Output:${RESET}"
                                echo "$result_json" | jq -C '.' 2>/dev/null | while IFS= read -r json_line; do
                                    echo -e "${BLUE}│${RESET}   $json_line"
                                done
                            fi
                        fi
                        
                        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
                        ;;
                esac
            fi
        fi
    done

    local end_time=$(date +%s.%N)
    local elapsed=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
    echo -e "\n${YELLOW}⚡ Completed in ${elapsed}s${RESET}\n"
}

# === SETUP FUNCTIONS ===

setup_environment() {
    if [ "$USE_DEFAULTS" = true ]; then
        echo -e "${YELLOW}Using environment: Localhost (default)${RESET}"
        return
    fi

    echo -e "${CYAN}Choose environment:${RESET}"
    echo -e "  ${GREEN}1)${RESET} Localhost (default) - $BASE_URL"
    echo -e "  ${GREEN}2)${RESET} Custom URL"
    read -p "> " ENV_CHOICE

    if [ "$ENV_CHOICE" = "2" ]; then
        read -p "Enter custom URL: " BASE_URL
        echo -e "${YELLOW}Using environment: $BASE_URL${RESET}"
    else
        echo -e "${YELLOW}Using environment: Localhost${RESET}"
    fi
}

setup_session() {
    if [ -n "$SESSION_ID" ]; then
        echo -e "${YELLOW}Using session: ${SESSION_ID}${RESET}"
    elif [ "$USE_DEFAULTS" = true ]; then
        SESSION_ID="session-$(uuidgen | tr '[:upper:]' '[:lower:]')"
        echo -e "${YELLOW}Generated session: ${SESSION_ID}${RESET}"
    else
        echo -e "${CYAN}Enter session ID (press Enter for auto-generated):${RESET}"
        read -p "> " SESSION_ID
        if [ -z "$SESSION_ID" ]; then
            SESSION_ID="session-$(uuidgen | tr '[:upper:]' '[:lower:]')"
            echo -e "${YELLOW}Generated session: ${SESSION_ID}${RESET}"
        fi
    fi
}

setup_user_id() {
    if [ -n "$USER_ID" ]; then
        echo -e "${YELLOW}Using userId: ${USER_ID}${RESET}"
    elif [ "$USE_DEFAULTS" = true ]; then
        USER_ID="$(whoami)"
        echo -e "${YELLOW}Using username: ${USER_ID}${RESET}"
    else
        echo -e "${CYAN}Enter user ID (press Enter to use $(whoami)):${RESET}"
        read -p "> " USER_ID
        if [ -z "$USER_ID" ]; then
            USER_ID="$(whoami)"
            echo -e "${YELLOW}Using username: ${USER_ID}${RESET}"
        fi
    fi
}

# === INTERACTIVE CHAT ===

run_interactive_chat() {
    echo -e "\n${GREEN}🔄 Interactive Chat Mode${RESET}"
    echo -e "${CYAN}Type your messages (type 'exit' to quit)${RESET}"

    while true; do
        echo
        read -p "${CYAN}[$(date '+%H:%M:%S')]${RESET} ${GREEN}You > ${RESET}" MESSAGE
        
        if [[ "$MESSAGE" == "exit" ]]; then
            echo -e "${YELLOW}Goodbye!${RESET}"
            break
        fi

        if [ -z "$MESSAGE" ]; then
            echo -e "${RED}❌ Please enter a message${RESET}"
            continue
        fi

        process_streaming_response "$MESSAGE"
    done
}

# === MAIN EXECUTION ===

while [[ $# -gt 0 ]]; do
    case $1 in
        --endpoint=*)
            ENDPOINT="${1#*=}"
            shift
            ;;
        --session-id=*)
            SESSION_ID="${1#*=}"
            shift
            ;;
        --user-id=*)
            USER_ID="${1#*=}"
            shift
            ;;
        --url=*)
            BASE_URL="${1#*=}"
            shift
            ;;
        --default)
            USE_DEFAULTS=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${RESET}"
            show_help
            ;;
    esac
done

if [ -z "$ENDPOINT" ]; then
    echo -e "${RED}Error: --endpoint is required${RESET}"
    echo -e "${YELLOW}Example: $0 --endpoint=stream-forecasting${RESET}"
    exit 1
fi

echo -e "${BOLD}${BLUE}🤖 AG-UI Streaming Chat${RESET}"
echo -e "${CYAN}Endpoint: ${WHITE}${ENDPOINT}${RESET}\n"

trap cleanup INT TERM EXIT

setup_environment
setup_session
setup_user_id

run_interactive_chat
