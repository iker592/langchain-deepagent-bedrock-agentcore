#!/bin/bash

GREEN=$(tput setaf 2)
CYAN=$(tput setaf 6)
YELLOW=$(tput setaf 3)
MAGENTA=$(tput setaf 5)
RED=$(tput setaf 1)
BLUE=$(tput setaf 4)
RESET=$(tput sgr0)

BASE_URL="${BASE_URL:-http://localhost:8001}"
USER_ID="${USER_ID:-testuser}"

echo -e "${YELLOW}🔄 Testing LangChain Agent Streaming${RESET}"
echo -e "${CYAN}Base URL: ${BASE_URL}${RESET}"
echo -e "${CYAN}User ID: ${USER_ID}${RESET}\n"

make_request() {
    local message="$1"
    local request_id=$(uuidgen)
    
    local request_body=$(cat <<EOF
{
  "id": "$request_id",
  "conversation": [
    {
      "role": "user",
      "message": "$message",
      "metadata": {}
    }
  ],
  "show_tool_calls": true
}
EOF
)
    
    echo -e "${MAGENTA}Query: ${message}${RESET}\n"
    echo -e "${YELLOW}---------- Streaming Response ----------${RESET}\n"
    
    curl -s --no-buffer -X POST "${BASE_URL}/stream-chat" \
        -H 'Content-Type: application/json' \
        -H 'Accept: text/event-stream' \
        -H "userId: ${USER_ID}" \
        -d "$request_body" | while IFS= read -r raw_line; do
        
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
                        echo -e "${GREEN}🚀 Run started${RESET}\n"
                        ;;
                    "TEXT_MESSAGE_START")
                        echo -en "${BLUE}🤖 Assistant: ${RESET}"
                        ;;
                    "TEXT_MESSAGE_CONTENT")
                        local delta=$(echo "$line" | jq -r '.delta // ""')
                        printf "%s" "$delta"
                        ;;
                    "TEXT_MESSAGE_END")
                        echo -e "\n"
                        ;;
                    "TOOL_CALL_START")
                        local tool_name=$(echo "$line" | jq -r '.toolCallName // .tool_call_name // "unknown"')
                        echo -e "\n${YELLOW}🔧 Tool: ${tool_name}${RESET}"
                        ;;
                    "TOOL_CALL_ARGS")
                        local delta=$(echo "$line" | jq -r '.delta // ""')
                        echo -en "${YELLOW}   Args: ${RESET}"
                        echo "$delta" | jq -C .
                        ;;
                    "TOOL_CALL_RESULT")
                        local content=$(echo "$line" | jq -r '.content // ""')
                        echo -e "${GREEN}   Result: ${content}${RESET}\n"
                        ;;
                    "RUN_FINISHED")
                        echo -e "${GREEN}✅ Run completed${RESET}"
                        ;;
                    "RUN_ERROR")
                        local error=$(echo "$line" | jq -r '.message // "unknown"')
                        echo -e "${RED}❌ Error: ${error}${RESET}"
                        ;;
                esac
            fi
        fi
    done
    
    echo -e "\n${YELLOW}----------------------------------------${RESET}\n"
}

if [ -n "$1" ]; then
    make_request "$1"
else
    echo -e "${CYAN}Choose a test:${RESET}"
    echo -e "  ${GREEN}1)${RESET} Simple calculation"
    echo -e "  ${GREEN}2)${RESET} Weather query"
    echo -e "  ${GREEN}3)${RESET} Tell a story"
    echo -e "  ${GREEN}4)${RESET} Greeting"
    echo -e "  ${GREEN}5)${RESET} Custom message"
    read -p "> " choice
    
    case $choice in
        1)
            make_request "What's 25 * 17?"
            ;;
        2)
            make_request "What's the weather in Seattle?"
            ;;
        3)
            make_request "Tell me a short story about a robot"
            ;;
        4)
            make_request "Greet Alice"
            ;;
        5)
            read -p "${CYAN}Enter your message: ${RESET}" custom_msg
            make_request "$custom_msg"
            ;;
        *)
            echo -e "${RED}Invalid choice${RESET}"
            exit 1
            ;;
    esac
fi

