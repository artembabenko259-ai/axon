package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/gorilla/websocket"
	"net/http"
	"bytes"
	"bufio"
)

var globalProgram *tea.Program

type wsMsg struct {
	Type    string  `json:"type"`
	Content string  `json:"content,omitempty"`
	Text    string  `json:"text,omitempty"`
	Delta   string  `json:"delta,omitempty"`
	Model   string  `json:"model,omitempty"`
	Token   string  `json:"token,omitempty"`
	Tool    string  `json:"tool,omitempty"`
	Status  string  `json:"status,omitempty"`
	Detail  string  `json:"detail,omitempty"`
	Tokens  int     `json:"tokens,omitempty"`
	Cost    float64 `json:"cost,omitempty"`
}

type wsConnectedMsg struct{}
type wsDisconnectedMsg struct{}
type wsModelMsg struct{ model string }
type wsStreamStartMsg struct{}
type wsStreamDeltaMsg struct{ delta string }
type wsStreamEndMsg struct{ text string }
type wsErrorMsg struct{ err string }
type wsToolEventMsg struct {
	Tool   string
	Status string
	Detail string
}
type wsPolicyMsg struct {
	AutopilotActive bool
	AutonomyEnabled bool
}
type wsStatsMsg struct {
	Tokens int
	Cost   float64
}
type wsHistoryMsg struct {
	messages []chatMessage
}

type command struct {
	Name        string
	Description string
}

var autocompleteCommands = []command{
	{"/help", "List available slash commands"},
	{"/exit", "Exit AXON"},
	{"/clear", "Clear chat context (keeps system prompt)"},
	{"/cost", "Show session cost and token usage"},
	{"/usage", "Alias for /cost"},
	{"/compact", "Summarize older messages to free context window"},
	{"/model", "Switch model — e.g. /model anthropic/claude-3.5-sonnet"},
	{"/plan", "Plan Mode — /plan <description> to break work into steps"},
	{"/execute", "Run the active plan step-by-step"},
	{"/tasks", "Toggle plan task side panel — F2"},
	{"/thinking", "Toggle AI reasoning trace in chat — F3"},
	{"/export-skill", "Export skill to .axon/exports — /export-skill <name>"},
	{"/session", "Toggle session timeline panel — F4"},
	{"/create-skill", "Interactive wizard to create a new SKILL.md"},
	{"/gen-skill", "AI-generate a skill from a description — /gen-skill \"...\""},
	{"/review", "Review current git diff for bugs and code smells"},
	{"/undo", "Restore last file overwritten by write_file"},
	{"/commit", "AI-generated Conventional Commit with confirmation"},
	{"/artifacts", "List and view project artifacts — /artifacts view <filename>"},
	{"/docs", "Generate and serve interactive project docs at localhost:8000"},
	{"/create-agent", "Scaffold a sub-agent in .axon/agents/"},
	{"/delegate", "Delegate task to sub-agent — /delegate <name> <task>"},
	{"/multitask", "Orchestrator — parallel subtasks — /multitask <goal>"},
	{"/config", "Runtime policy — /config | /config set <key> <value>"},
	{"/provider", "LLM provider — /provider | /provider custom <url> <key>"},
	{"/autopilot", "Autopilot full autonomy — /autopilot on|off|status"},
	{"/system", "Session/global system prompt — /system session|global|edit|clear"},
	{"/sessions", "List saved chat sessions"},
	{"/resume", "Resume session — /resume <id>"},
	{"/save", "Save current session — /save [title]"},
	{"/export", "Export session to Markdown — /export [path]"},
	{"/mcp", "MCP servers — /mcp list | /mcp add <name> <command...>"},
	{"/login", "Sign in via runaxon.xyz — opens browser for email registration"},
	{"/logout", "Sign out of AXON account on this machine"},
	{"/skills", "Manage custom skills / integrations — /skills list|enable|disable|install <name>"},
}

type messageType int

const (
	msgUser messageType = iota
	msgAxonText
	msgTool
)

type chatMessage struct {
	Type       messageType
	Content    string
	ToolName   string
	ToolStatus string
	ToolDetail string
}

// Styling Theme
var (
	bgColor      = lipgloss.Color("#121212")
	borderColor  = lipgloss.Color("#333333")
	textColor    = lipgloss.Color("#d4d4d4")
	mutedColor   = lipgloss.Color("#737373")
	accentColor  = lipgloss.Color("#a3a3a3")

	headerStyle = lipgloss.NewStyle().
			Border(lipgloss.NormalBorder(), false, false, true, false).
			BorderForeground(borderColor).
			Padding(0, 1).
			Bold(true).
			Foreground(accentColor)

	statusStyle = lipgloss.NewStyle().
			Foreground(mutedColor)

	borderLineStyle = lipgloss.NewStyle().
			Foreground(borderColor)
)

func loadBridgeToken() string {
	appData := os.Getenv("APPDATA")
	var path string
	if appData != "" {
		path = filepath.Join(appData, "AXON", "runtime_policy.json")
	} else {
		home, _ := os.UserHomeDir()
		path = filepath.Join(home, ".config", "AXON", "runtime_policy.json")
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	var policy struct {
		BridgeToken string `json:"bridge_token"`
	}
	if err := json.Unmarshal(data, &policy); err != nil {
		return ""
	}
	return policy.BridgeToken
}

type fileActivity struct {
	Path   string
	Action string
	Status string
}

type model struct {
	conn                *websocket.Conn
	textInput           textinput.Model
	viewport            viewport.Model
	messages            []chatMessage
	currentMsg          string
	currentModel        string
	status              string
	width               int
	height              int
	connected           bool
	showSuggestions     bool
	filteredSuggestions []command
	suggestionIdx       int
	autopilotActive     bool
	autonomyEnabled     bool
	securityMode        int // 0 = def, 1 = accept edit, 2 = bypass
	totalTokens         int
	totalCost           float64
	splitPanes          bool
	expandedThinking    bool
	tickCount           int
	activeFiles         []fileActivity
}

func initialModel(conn *websocket.Conn) model {
	ti := textinput.New()
	ti.Placeholder = "Ask AXON anything... (type @ for files, / for commands)"
	ti.Focus()
	ti.CharLimit = 4096
	ti.Prompt = " ❯ "
	ti.PromptStyle = lipgloss.NewStyle().Foreground(accentColor).Bold(true)

	vp := viewport.New(80, 20)
	vp.SetContent("[..] Connecting to AXON core bridge...")

	return model{
		conn:             conn,
		textInput:        ti,
		viewport:         vp,
		messages:         []chatMessage{},
		currentModel:     "detecting...",
		status:           "CONNECTING",
		connected:        false,
		splitPanes:       true, // enabled by default to showcase layout
		expandedThinking: false,
		securityMode:     0,
		activeFiles:      []fileActivity{},
	}
}

func (m model) getWelcomeMessage() string {
	mascot := `
  ▄███▄          ▄███▄
  ██ ██          ██ ██
  ▀███▀  ▄▄▄██▄▄▄  ▀███▀
   ▄████████████████▄
  ▐██████████████████▌
   ▀███▀ ▀████▀ ▀███▀
   ▄   ▄          ▄   ▄
`
	mascotColor := "#ef4444"

	if os.Getenv("AXON_DART_MODE") == "1" {
		mascot = `
      ▄█▄
    ▄█████▄
   ▐██▀█▀██▌
   ▐██▄█▄██▌
    ▀█████▀
      ▀█▀
`
		mascotColor = "#ff3333"
	}

	urlStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#38bdf8")).Underline(true)
	panelURL := urlStyle.Render("http://127.0.0.1:3000")

	// Seed local random generator
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	var mascotText string

	if os.Getenv("AXON_DART_MODE") == "1" {
		variations := []string{
			" Welcome to AXON Dart!\n Binary targets loaded.\n Let's decompile the world!\n\n Control Panel: %s",
			" Welcome to AXON Dart!\n Finding entry points and symbols...\n Ready to decompile and analyze.\n\n Control Panel: %s",
			" Welcome to AXON Dart!\n Memory mapping initialized.\n Let's scan for zero-days!\n\n Control Panel: %s",
			" Welcome to AXON Dart!\n Bytecode parsing complete.\n Time to decode the logic.\n\n Control Panel: %s",
		}
		mascotText = fmt.Sprintf(variations[r.Intn(len(variations))], panelURL)
	} else {
		variations := []string{
			" Welcome to AXON Shard!\n I'm your agentic companion.\n Let's build something awesome!\n\n Control Panel: %s",
			" Welcome to AXON Shard!\n Seven minutes is all I can spare\n to play with you...\n\n Control Panel: %s",
			" Welcome to AXON Shard!\n I have only 7 minutes for this task.\n Let's make every second count!\n\n Control Panel: %s",
			" Welcome to AXON Shard!\n System online. Autopilot standby.\n Let's code something legendary!\n\n Control Panel: %s",
		}
		mascotText = fmt.Sprintf(variations[r.Intn(len(variations))], panelURL)
	}

	helpText := `
* Type a message to chat, or type / for commands.

* Common Commands:
  /help      - View full help guide
  /plan      - Start planning a project step-by-step
  /multitask - Run multiple sub-agents in parallel
  /artifacts - View or open generated files
  /clear     - Clear screen
  /exit      - Close this terminal UI

* Shortcuts:
  Tab        - Auto-complete command suggestions
  Ctrl+C     - Quit AXON Shard immediately
`

	mascotBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderColor).
		Padding(1, 2).
		Foreground(lipgloss.Color(mascotColor)).
		Render(mascot)

	mascotTextBox := lipgloss.NewStyle().
		Padding(2, 1).
		Foreground(textColor).
		Render(mascotText)

	mascotBlock := lipgloss.JoinHorizontal(lipgloss.Center, mascotBox, mascotTextBox)

	helpBox := lipgloss.NewStyle().
		Padding(1, 2).
		Render(helpText)

	return lipgloss.JoinVertical(lipgloss.Left, mascotBlock, helpBox)
}

func (m model) renderMessages() string {
	if len(m.messages) == 0 {
		return m.getWelcomeMessage()
	}

	var sb strings.Builder
	for _, msg := range m.messages {
		switch msg.Type {
		case msgUser:
			sb.WriteString(fmt.Sprintf("\n❯ You:\n%s\n", msg.Content))
		case msgAxonText:
			thinking, answer, hasT, isComp := parseThinking(msg.Content)
			if hasT {
				var thinkBlock string
				if !isComp {
					frames := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
					frame := frames[m.tickCount%len(frames)]
					thinkBlock = lipgloss.NewStyle().
						Foreground(mutedColor).
						Border(lipgloss.NormalBorder(), false, false, false, true).
						BorderForeground(lipgloss.Color("#eab308")).
						Padding(0, 1).
						Render(fmt.Sprintf("%s Thinking...\n%s", frame, thinking))
				} else {
					if m.expandedThinking {
						thinkBlock = lipgloss.NewStyle().
							Foreground(mutedColor).
							Border(lipgloss.NormalBorder(), false, false, false, true).
							BorderForeground(accentColor).
							Padding(0, 1).
							Render(fmt.Sprintf("▼ Thoughts\n%s", thinking))
					} else {
						thinkBlock = lipgloss.NewStyle().
							Foreground(mutedColor).
							Render("▶ Show Thoughts (Press F3 to expand)")
					}
				}
				if answer != "" {
					sb.WriteString(fmt.Sprintf("\n✦ AXON:\n%s\n\n%s\n", thinkBlock, formatLatexMath(answer)))
				} else {
					sb.WriteString(fmt.Sprintf("\n✦ AXON:\n%s\n", thinkBlock))
				}
			} else {
				sb.WriteString(fmt.Sprintf("\n✦ AXON:\n%s\n", formatLatexMath(msg.Content)))
			}
		case msgTool:
			dot := ""
			statusText := ""
			switch msg.ToolStatus {
			case "start", "running":
				dot = lipgloss.NewStyle().Foreground(lipgloss.Color("#eab308")).Render("●") // Yellow
				statusText = lipgloss.NewStyle().Foreground(mutedColor).Render(" running...")
			case "done", "complete", "success":
				dot = lipgloss.NewStyle().Foreground(lipgloss.Color("#22c55e")).Render("●") // Green
			case "error", "failed":
				dot = lipgloss.NewStyle().Foreground(lipgloss.Color("#ef4444")).Render("●") // Red
				statusText = lipgloss.NewStyle().Foreground(lipgloss.Color("#ef4444")).Render(" failed")
			}

			detail := msg.ToolDetail
			if detail == "" {
				detail = msg.ToolName
			}
			sb.WriteString(fmt.Sprintf("\n %s %s%s\n", dot, detail, statusText))
		}
	}
	return sb.String()
}

func (m model) Init() tea.Cmd {
	return textinput.Blink
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		if m.showSuggestions && len(m.filteredSuggestions) > 0 {
			switch msg.Type {
			case tea.KeyTab:
				selected := m.filteredSuggestions[m.suggestionIdx].Name
				val := m.textInput.Value()
				lastAtIdx := strings.LastIndex(val, "@")
				if lastAtIdx != -1 && !strings.Contains(val[lastAtIdx:], " ") {
					newValue := val[:lastAtIdx] + selected
					m.textInput.SetValue(newValue)
					m.textInput.SetCursor(len(newValue))
				} else {
					m.textInput.SetValue(selected + " ")
					m.textInput.SetCursor(len(selected) + 1)
				}
				m.showSuggestions = false
				return m, nil
			case tea.KeyDown:
				m.suggestionIdx = (m.suggestionIdx + 1) % len(m.filteredSuggestions)
				return m, nil
			case tea.KeyUp:
				m.suggestionIdx = (m.suggestionIdx - 1 + len(m.filteredSuggestions)) % len(m.filteredSuggestions)
				return m, nil
			case tea.KeyEsc:
				m.showSuggestions = false
				return m, nil
			case tea.KeyEnter:
				selected := m.filteredSuggestions[m.suggestionIdx].Name
				val := m.textInput.Value()
				lastAtIdx := strings.LastIndex(val, "@")
				if lastAtIdx != -1 && !strings.Contains(val[lastAtIdx:], " ") {
					newValue := val[:lastAtIdx] + selected
					m.textInput.SetValue(newValue)
					m.textInput.SetCursor(len(newValue))
				} else {
					m.textInput.SetValue(selected + " ")
					m.textInput.SetCursor(len(selected) + 1)
				}
				m.showSuggestions = false
				return m, nil
			}
		}

		// Handle F3/F5 toggles
		if msg.String() == "f3" {
			m.expandedThinking = !m.expandedThinking
			m.viewport.SetContent(m.renderMessages())
			return m, nil
		}
		if msg.String() == "f5" {
			m.splitPanes = !m.splitPanes
			m.viewport.SetContent(m.renderMessages())
			return m, nil
		}

		switch msg.Type {
		case tea.KeyCtrlC:
			return m, tea.Quit
		case tea.KeyShiftTab:
			m.securityMode = (m.securityMode + 1) % 3
			modeStr := "def"
			if m.securityMode == 1 {
				modeStr = "accept_edit"
			} else if m.securityMode == 2 {
				modeStr = "bypass"
			}
			chatMsg := wsMsg{Type: "set_security_mode", Content: modeStr}
			data, _ := json.Marshal(chatMsg)
			if m.conn != nil {
				m.conn.WriteMessage(websocket.TextMessage, data)
			}
			return m, nil
		case tea.KeyEsc:
			if m.status == "THINKING" || m.status == "RUNNING TOOL" {
				chatMsg := wsMsg{Type: "abort"}
				data, _ := json.Marshal(chatMsg)
				_ = m.conn.WriteMessage(websocket.TextMessage, data)
				m.status = "READY"
				m.messages = append(m.messages, chatMessage{
					Type:    msgAxonText,
					Content: "\n[Generation aborted by user]\n",
				})
				m.viewport.SetContent(m.renderMessages())
				m.viewport.GotoBottom()
				return m, nil
			}
			return m, tea.Quit
		case tea.KeyEnter:
			input := strings.TrimSpace(m.textInput.Value())
			if input == "" {
				break
			}
			if input == "/exit" || input == "/quit" {
				return m, tea.Quit
			}
			if input == "/clear" {
				m.messages = []chatMessage{}
				m.viewport.SetContent(m.getWelcomeMessage())
				m.viewport.GotoTop()
				m.textInput.SetValue("")
				m.showSuggestions = false
				break
			}

			// Parse file attachments
			var attachedText strings.Builder
			attachedText.WriteString(input)

			words := strings.Fields(input)
			for _, word := range words {
				if strings.HasPrefix(word, "@") {
					filename := word[1:]
					data, err := os.ReadFile(filename)
					if err == nil {
						content := string(data)
						if len(content) > 15000 {
							content = content[:15000] + "\n... [content truncated to 15KB] ..."
						}
						attachedText.WriteString(fmt.Sprintf("\n\n--- Attached File: %s ---\n%s\n-------------------------", filename, content))
					}
				}
			}

			if true {
				// Send to websocket (always use python daemon for tools and history)
				chatMsg := wsMsg{
					Type: "chat",
					Text: attachedText.String(),
				}
				data, _ := json.Marshal(chatMsg)
				_ = m.conn.WriteMessage(websocket.TextMessage, data)

				// Record user message
				m.messages = append(m.messages, chatMessage{
					Type:    msgUser,
					Content: input,
				})
				m.viewport.SetContent(m.renderMessages())
				m.viewport.GotoBottom()


				m.textInput.SetValue("")
				m.status = "THINKING"
				m.showSuggestions = false
			}

		default:
			m.textInput, cmd = m.textInput.Update(msg)
			cmds = append(cmds, cmd)

			val := m.textInput.Value()
			lastAtIdx := strings.LastIndex(val, "@")
			if lastAtIdx != -1 && !strings.Contains(val[lastAtIdx:], " ") {
				prefix := val[lastAtIdx+1:]
				m.filteredSuggestions = []command{}
				matches, _ := filepath.Glob(prefix + "*")
				for _, match := range matches {
					stat, err := os.Stat(match)
					if err == nil && !stat.IsDir() {
						m.filteredSuggestions = append(m.filteredSuggestions, command{
							Name:        "@" + match,
							Description: fmt.Sprintf("Attach file (%d bytes)", stat.Size()),
						})
					}
				}
				if len(m.filteredSuggestions) > 6 {
					m.filteredSuggestions = m.filteredSuggestions[:6]
				}
				m.showSuggestions = len(m.filteredSuggestions) > 0
				if m.suggestionIdx >= len(m.filteredSuggestions) {
					m.suggestionIdx = 0
				}
			} else if strings.HasPrefix(val, "/") {
				m.filteredSuggestions = []command{}
				for _, c := range autocompleteCommands {
					if strings.HasPrefix(c.Name, val) {
						m.filteredSuggestions = append(m.filteredSuggestions, c)
					}
				}
				m.showSuggestions = len(m.filteredSuggestions) > 0
				if m.suggestionIdx >= len(m.filteredSuggestions) {
					m.suggestionIdx = 0
				}
			} else {
				m.showSuggestions = false
			}
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

		viewportHeight := m.height - 6
		viewportHeight -= m.popupHeight()
		if viewportHeight < 1 {
			viewportHeight = 1
		}

		m.viewport.Width = msg.Width
		m.viewport.Height = viewportHeight
		m.textInput.Width = msg.Width - 6

		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsConnectedMsg:
		m.connected = true
		m.status = "READY"
		m.viewport.SetContent(m.getWelcomeMessage())

	case wsDisconnectedMsg:
		m.connected = false
		m.status = "DISCONNECTED"
		m.messages = append(m.messages, chatMessage{
			Type:    msgUser,
			Content: "[Connection closed]",
		})
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsModelMsg:
		m.currentModel = msg.model

	case wsStreamStartMsg:
		m.currentMsg = ""
		m.messages = append(m.messages, chatMessage{
			Type:    msgAxonText,
			Content: "",
		})
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsStreamDeltaMsg:
		m.tickCount++
		m.currentMsg += msg.delta
		for i := len(m.messages) - 1; i >= 0; i-- {
			if m.messages[i].Type == msgAxonText {
				m.messages[i].Content = m.currentMsg
				break
			}
		}
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsStreamEndMsg:
		m.status = "READY"
		for i := len(m.messages) - 1; i >= 0; i-- {
			if m.messages[i].Type == msgAxonText {
				m.messages[i].Content = msg.text
				break
			}
		}
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsPolicyMsg:
		m.autopilotActive = msg.AutopilotActive
		m.autonomyEnabled = msg.AutonomyEnabled
		m.viewport.SetContent(m.renderMessages())

	case wsStatsMsg:
		m.totalTokens = msg.Tokens
		m.totalCost = msg.Cost
		m.viewport.SetContent(m.renderMessages())

	case wsHistoryMsg:
		m.messages = msg.messages
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsErrorMsg:
		m.status = "READY"
		m.messages = append(m.messages, chatMessage{
			Type:    msgAxonText,
			Content: "❌ Error: " + msg.err,
		})
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsToolEventMsg:
		m = m.updateFileActivity(msg.Tool, msg.Status, msg.Detail)
		if msg.Status == "start" {
			m.status = "RUNNING TOOL"
			m.messages = append(m.messages, chatMessage{
				Type:       msgTool,
				ToolName:   msg.Tool,
				ToolStatus: "start",
				ToolDetail: msg.Detail,
			})
		} else {
			m.status = "READY"
			for i := len(m.messages) - 1; i >= 0; i-- {
				if m.messages[i].Type == msgTool && m.messages[i].ToolName == msg.Tool {
					m.messages[i].ToolStatus = msg.Status
					if msg.Detail != "" {
						m.messages[i].ToolDetail = msg.Detail
					}
					break
				}
			}
		}
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()
	}

	viewportHeight := m.height - 6
	viewportHeight -= m.popupHeight()
	if viewportHeight < 1 {
		viewportHeight = 1
	}
	if m.viewport.Height != viewportHeight {
		m.viewport.Height = viewportHeight
		m.viewport.GotoBottom()
	}

	if len(m.messages) > 300 {
		m.messages = m.messages[len(m.messages)-300:]
	}

	return m, tea.Batch(cmds...)
}

func (m model) popupHeight() int {
	if !m.showSuggestions || len(m.filteredSuggestions) == 0 {
		return 0
	}
	h := len(m.filteredSuggestions)
	if h > 5 {
		h = 5 + 1
	}
	return h + 2
}

func (m model) autocompleteView() string {
	if !m.showSuggestions || len(m.filteredSuggestions) == 0 {
		return ""
	}

	maxVisible := 5
	start := 0
	end := len(m.filteredSuggestions)
	if end > maxVisible {
		start = m.suggestionIdx - maxVisible/2
		if start < 0 {
			start = 0
		}
		end = start + maxVisible
		if end > len(m.filteredSuggestions) {
			end = len(m.filteredSuggestions)
			start = end - maxVisible
		}
	}

	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Foreground(borderColor).Render(" ┌" + strings.Repeat("─", m.width-6) + "┐") + "\n")

	for i := start; i < end; i++ {
		cmd := m.filteredSuggestions[i]
		style := lipgloss.NewStyle().Padding(0, 2)
		if i == m.suggestionIdx {
			style = style.
				Background(lipgloss.Color("#262626")).
				Foreground(lipgloss.Color("#ffffff")).
				Bold(true)
		} else {
			style = style.Foreground(textColor)
		}

		cmdStr := fmt.Sprintf("%-14s  %s", cmd.Name, cmd.Description)
		if len(cmdStr) > m.width-10 {
			cmdStr = cmdStr[:m.width-13] + "..."
		}

		paddedLine := style.Render(fmt.Sprintf(" %-*s", m.width-8, cmdStr))
		sb.WriteString(paddedLine + "\n")
	}

	if len(m.filteredSuggestions) > maxVisible {
		hint := fmt.Sprintf(" ... (item %d of %d, use Up/Down/Tab to scroll) ...", m.suggestionIdx+1, len(m.filteredSuggestions))
		hintStyle := lipgloss.NewStyle().Foreground(mutedColor).Padding(0, 2)
		paddedHint := hintStyle.Render(fmt.Sprintf(" %-*s", m.width-8, hint))
		sb.WriteString(paddedHint + "\n")
	}

	sb.WriteString(lipgloss.NewStyle().Foreground(borderColor).Render(" └" + strings.Repeat("─", m.width-6) + "┘"))
	return sb.String()
}

func (m model) View() string {
	if m.width == 0 || m.height == 0 {
		return "Loading UI..."
	}

	// 1. Header
	headerText := fmt.Sprintf(" AXON SHARD   │   Model: %s", m.currentModel)
	header := headerStyle.Width(m.width - 2).Render(headerText)

	// 2. Chat history viewport & Right Panels
	var mainChatArea string
	if m.splitPanes && m.width > 60 {
		leftWidth := (m.width * 7) / 10
		rightWidth := m.width - leftWidth - 6

		m.viewport.Width = leftWidth
		leftView := m.viewport.View()

		viewportHeight := m.viewport.Height
		rTopHeight := viewportHeight / 2
		rBotHeight := viewportHeight - rTopHeight - 2
		if rBotHeight < 1 {
			rBotHeight = 1
		}

		rightTop := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(borderColor).
			Padding(0, 1).
			Width(rightWidth).
			Height(rTopHeight).
			Render(m.renderAutopilotStatus(rightWidth, rTopHeight))

		rightBot := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(borderColor).
			Padding(0, 1).
			Width(rightWidth).
			Height(rBotHeight).
			Render(m.renderTelemetryStatus(rightWidth, rBotHeight))

		rightPanel := lipgloss.JoinVertical(lipgloss.Left, rightTop, rightBot)
		mainChatArea = lipgloss.JoinHorizontal(lipgloss.Top, leftView, "   ", rightPanel)
	} else {
		m.viewport.Width = m.width
		mainChatArea = m.viewport.View()
	}

	// 3. Autocomplete popup
	popup := m.autocompleteView()

	// 4. Border line
	borderLine := borderLineStyle.Render(strings.Repeat("─", m.width))

	// 5. Text input field
	input := m.textInput.View()

	// 6. Status bar
	statusText := fmt.Sprintf("  Status: %s   │   F3 thinking   │   F5 panels   │   Esc cancel", m.status)
	if m.width > 90 {
		statusText = fmt.Sprintf("  Status: %s   │   F3 thinking   │   F5 panels   │   Esc cancel   │   Zenith Panel: http://127.0.0.1:3000   │   Ctrl+C to quit", m.status)
	}
	footer := statusStyle.Render(statusText)

	if popup != "" {
		return lipgloss.JoinVertical(
			lipgloss.Left,
			header,
			mainChatArea,
			popup,
			borderLine,
			input,
			footer,
		)
	}

	return lipgloss.JoinVertical(
		lipgloss.Left,
		header,
		mainChatArea,
		borderLine,
		input,
		footer,
	)
}

func main() {
	if os.Getenv("AXON_DART_MODE") == "1" {
		bgColor = lipgloss.Color("#0d0202")
		borderColor = lipgloss.Color("#3a0a0a")
		textColor = lipgloss.Color("#ff3333")
		mutedColor = lipgloss.Color("#801515")
		accentColor = lipgloss.Color("#ff0000")
	}

	u := url.URL{Scheme: "ws", Host: "127.0.0.1:8765", Path: "/"}
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatalf("[!] Error connecting to bridge: %v\nMake sure AXON serve or AXON repl is running in the background.", err)
	}
	defer conn.Close()

	p := tea.NewProgram(initialModel(conn), tea.WithAltScreen())
	globalProgram = p

	go func() {
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				p.Send(wsDisconnectedMsg{})
				return
			}

			var msg wsMsg
			if err := json.Unmarshal(message, &msg); err != nil {
				continue
			}

			switch msg.Type {
			case "auth_required":
				token := loadBridgeToken()
				authMsg := wsMsg{Type: "auth", Token: token}
				b, _ := json.Marshal(authMsg)
				_ = conn.WriteMessage(websocket.TextMessage, b)

			case "connected":
				p.Send(wsConnectedMsg{})

			case "model":
				p.Send(wsModelMsg{model: msg.Model})

			case "stream_start":
				p.Send(wsStreamStartMsg{})

			case "stream_delta":
				p.Send(wsStreamDeltaMsg{delta: msg.Delta})

			case "stream_end":
				p.Send(wsStreamEndMsg{text: msg.Text})

			case "error":
				p.Send(wsErrorMsg{err: msg.Content})

			case "tool_event":
				p.Send(wsToolEventMsg{
					Tool:   msg.Tool,
					Status: msg.Status,
					Detail: msg.Detail,
				})

			case "policy":
				var policyData struct {
					Policy struct {
						AutopilotActive bool `json:"autopilot_active"`
						AutonomyEnabled bool `json:"autonomy_enabled"`
					} `json:"policy"`
				}
				_ = json.Unmarshal(message, &policyData)
				p.Send(wsPolicyMsg{
					AutopilotActive: policyData.Policy.AutopilotActive,
					AutonomyEnabled: policyData.Policy.AutonomyEnabled,
				})

			case "stats":
				p.Send(wsStatsMsg{
					Tokens: msg.Tokens,
					Cost:   msg.Cost,
				})

			case "history":
				var histData struct {
					History []struct {
						Type    string `json:"type"`
						Role    string `json:"role"`
						Text    string `json:"text"`
						Tool    string `json:"tool"`
						Status  string `json:"status"`
						Detail  string `json:"detail"`
					} `json:"history"`
				}
				_ = json.Unmarshal(message, &histData)

				var histMsgs []chatMessage
				for _, item := range histData.History {
					if item.Type == "chat" {
						roleType := msgUser
						if item.Role == "assistant" {
							roleType = msgAxonText
						}
						histMsgs = append(histMsgs, chatMessage{
							Type:    roleType,
							Content: item.Text,
						})
					} else if item.Type == "tool_event" {
						histMsgs = append(histMsgs, chatMessage{
							Type:       msgTool,
							ToolName:   item.Tool,
							ToolStatus: item.Status,
							ToolDetail: item.Detail,
						})
					}
				}
				p.Send(wsHistoryMsg{messages: histMsgs})
			}
		}
	}()

	finalModel, err := p.Run()
	if err != nil {
		log.Fatal(err)
	}
	if m, ok := finalModel.(model); ok {
		m.saveSession()
	}
}

var latexUnicode = map[string]string{
	"\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ", "\\epsilon": "ε",
	"\\zeta": "ζ", "\\eta": "η", "\\theta": "θ", "\\iota": "ι", "\\kappa": "κ",
	"\\lambda": "λ", "\\mu": "μ", "\\nu": "ν", "\\xi": "ξ", "\\omicron": "ο",
	"\\pi": "π", "\\rho": "ρ", "\\sigma": "σ", "\\tau": "τ", "\\upsilon": "υ",
	"\\phi": "φ", "\\chi": "χ", "\\psi": "ψ", "\\omega": "ω",
	"\\Gamma": "Γ", "\\Delta": "Δ", "\\Theta": "Θ", "\\Lambda": "Λ", "\\Xi": "Ξ",
	"\\Pi": "Π", "\\Sigma": "Σ", "\\Upsilon": "Υ", "\\Phi": "Φ", "\\Psi": "Ψ",
	"\\Omega": "Ω",
	"\\infty": "∞", "\\partial": "∂", "\\nabla": "∇", "\\int": "∫", "\\iint": "∬",
	"\\iiint": "∭", "\\oint": "∮", "\\sum": "∑", "\\prod": "∏", "\\coprod": "∐",
	"\\times": "×", "\\div": "÷", "\\pm": "±", "\\mp": "∓", "\\neq": "≠",
	"\\approx": "≈", "\\propto": "∝", "\\equiv": "≡", "\\le": "≤", "\\ge": "≥",
	"\\leq": "≤", "\\geq": "≥", "\\ll": "≪", "\\gg": "≫", "\\in": "∈",
	"\\ni": "∋", "\\notin": "∉", "\\subset": "⊂", "\\supset": "⊃", "\\subseteq": "⊆",
	"\\supseteq": "⊇", "\\cap": "∩", "\\cup": "∪", "\\land": "∧", "\\lor": "∨",
	"\\neg": "¬", "\\forall": "∀", "\\exists": "∃", "\\hbar": "ℏ",
	"\\cdot": "·", "\\to": "→", "\\rightarrow": "→", "\\leftarrow": "←",
	"\\impliedby": "⇐", "\\implies": "⇒", "\\iff": "⇔",
}

var superscripts = map[rune]rune{
	'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
	'+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'x': 'ˣ', 'y': 'ʸ', 'i': 'ⁱ', 'j': 'ʲ',
}

var subscripts = map[rune]rune{
	'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
	'+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'i': 'ᵢ',
	'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ', 's': 'ₛ', 't': 'ₜ',
}

func cleanExpr(expr string) string {
	for cmd, uni := range latexUnicode {
		expr = strings.ReplaceAll(expr, cmd, uni)
	}

	reSupBracket := regexp.MustCompile(`\^\{([^}]+)\}`)
	expr = reSupBracket.ReplaceAllStringFunc(expr, func(m string) string {
		content := reSupBracket.FindStringSubmatch(m)[1]
		var sb strings.Builder
		for _, r := range content {
			if val, ok := superscripts[r]; ok {
				sb.WriteRune(val)
			} else {
				sb.WriteRune(r)
			}
		}
		return sb.String()
	})

	reSupSingle := regexp.MustCompile(`\^([0-9a-zA-Z+\-()=])`)
	expr = reSupSingle.ReplaceAllStringFunc(expr, func(m string) string {
		content := reSupSingle.FindStringSubmatch(m)[1]
		var sb strings.Builder
		for _, r := range content {
			if val, ok := superscripts[r]; ok {
				sb.WriteRune(val)
			} else {
				sb.WriteRune(r)
			}
		}
		return sb.String()
	})

	reSubBracket := regexp.MustCompile(`_\{([^}]+)\}`)
	expr = reSubBracket.ReplaceAllStringFunc(expr, func(m string) string {
		content := reSubBracket.FindStringSubmatch(m)[1]
		var sb strings.Builder
		for _, r := range content {
			if val, ok := subscripts[r]; ok {
				sb.WriteRune(val)
			} else {
				sb.WriteRune(r)
			}
		}
		return sb.String()
	})

	reSubSingle := regexp.MustCompile(`_([0-9a-zA-Z+\-()=])`)
	expr = reSubSingle.ReplaceAllStringFunc(expr, func(m string) string {
		content := reSubSingle.FindStringSubmatch(m)[1]
		var sb strings.Builder
		for _, r := range content {
			if val, ok := subscripts[r]; ok {
				sb.WriteRune(val)
			} else {
				sb.WriteRune(r)
			}
		}
		return sb.String()
	})

	reFrac := regexp.MustCompile(`\\frac\{([^}]+)\}\{([^}]+)\}`)
	expr = reFrac.ReplaceAllString(expr, `($1)/($2)`)

	reSqrt := regexp.MustCompile(`\\sqrt\{([^}]+)\}`)
	expr = reSqrt.ReplaceAllString(expr, `√($1)`)

	return strings.TrimSpace(expr)
}

func formatLatexMath(text string) string {
	reDisplay := regexp.MustCompile(`(?s)\$\$(.*?)\$\$|\\\[(.*?)\\\]`)
	text = reDisplay.ReplaceAllStringFunc(text, func(m string) string {
		sub := reDisplay.FindStringSubmatch(m)
		formulaRaw := sub[1]
		if formulaRaw == "" && len(sub) > 2 {
			formulaRaw = sub[2]
		}
		formula := cleanExpr(formulaRaw)
		width := len(formula) + 6
		borderTop := "┌" + strings.Repeat("─", width-2) + "┐"
		content := fmt.Sprintf("│   %s   │", formula)
		borderBot := "└" + strings.Repeat("─", width-2) + "┘"
		return fmt.Sprintf("\n%s\n%s\n%s\n", borderTop, content, borderBot)
	})

	reInline := regexp.MustCompile(`\$([^$]+)\$|\\\((.*?)\\\)`)
	text = reInline.ReplaceAllStringFunc(text, func(m string) string {
		sub := reInline.FindStringSubmatch(m)
		formulaRaw := sub[1]
		if formulaRaw == "" && len(sub) > 2 {
			formulaRaw = sub[2]
		}
		formula := cleanExpr(formulaRaw)
		return fmt.Sprintf(" *%s* ", formula)
	})

	return text
}

func parseThinking(content string) (thinking string, answer string, hasThinking bool, isComplete bool) {
	startIdx := strings.Index(content, "<thinking>")
	if startIdx == -1 {
		// Also support custom markdown tag block formats if they occur
		startIdx = strings.Index(content, "<thought>")
		if startIdx == -1 {
			return "", content, false, false
		}
		endIdx := strings.Index(content, "</thought>")
		if endIdx == -1 {
			thinking = content[startIdx+9:]
			answer = ""
			return thinking, answer, true, false
		}
		thinking = content[startIdx+9 : endIdx]
		answer = content[endIdx+10:]
		return thinking, answer, true, true
	}

	endIdx := strings.Index(content, "</thinking>")
	if endIdx == -1 {
		thinking = content[startIdx+10:]
		answer = ""
		return thinking, answer, true, false
	}

	thinking = content[startIdx+10 : endIdx]
	answer = content[endIdx+11:]
	return thinking, answer, true, true
}

func (m model) renderAutopilotStatus(width int, height int) string {
	status := "INACTIVE"
	statusColor := lipgloss.Color("#ef4444") // Red
	if m.autopilotActive || m.autonomyEnabled {
		status = "ACTIVE (Fully Autonomous)"
		statusColor = lipgloss.Color("#22c55e") // Green
	}

	header := lipgloss.NewStyle().Foreground(accentColor).Bold(true).Render("Autopilot Panel")
	statusLabel := lipgloss.NewStyle().Foreground(statusColor).Bold(true).Render(status)

	modeText := "DEF (Спрашивать всё)"
	if m.securityMode == 1 {
		modeText = "EDIT (Файлы без спроса)"
	} else if m.securityMode == 2 {
		modeText = "BYPASS (Полное доверие)"
	}
	modeLabel := lipgloss.NewStyle().Foreground(lipgloss.Color("#fbbf24")).Bold(true).Render("🛡 Security: " + modeText + " [Shift+Tab]")

	body := fmt.Sprintf("\n%s\n\nStatus: %s\n\n%s\n\n• auto-approves runs\n• auto-writes files\n• safe approval bridge\n• F5 to collapse panels", header, statusLabel, modeLabel)
	return body
}

func (m model) renderTelemetryStatus(width int, height int) string {
	header := lipgloss.NewStyle().Foreground(accentColor).Bold(true).Render("Telemetry & Activity")
	costStr := fmt.Sprintf("Session Cost:   $%.4f", m.totalCost)
	tokensStr := fmt.Sprintf("Session Tokens: %d", m.totalTokens)

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("\n%s\n\n%s\n%s\n\n", header, costStr, tokensStr))
	
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#71717a")).Bold(true).Render("Agent Activity (Files/Tools):") + "\n")
	
	if len(m.activeFiles) == 0 {
		sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#52525b")).Render("  No activity yet...") + "\n")
	} else {
		for _, f := range m.activeFiles {
			indicator := "●"
			color := lipgloss.Color("#fbbf24") // Amber for ACTIVE
			if f.Status == "OK" {
				indicator = "✓"
				color = lipgloss.Color("#10b981") // Green for OK
			} else if f.Status == "ERROR" {
				indicator = "✗"
				color = lipgloss.Color("#ef4444") // Red for ERROR
			}
			
			actionStr := lipgloss.NewStyle().Foreground(accentColor).Bold(true).Render(f.Action)
			pathStr := lipgloss.NewStyle().Foreground(lipgloss.Color("#e4e4e7")).Render(f.Path)
			indicatorStr := lipgloss.NewStyle().Foreground(color).Render(indicator)
			
			line := fmt.Sprintf("  %s %-6s %s", indicatorStr, actionStr, pathStr)
			if len(line) > width - 2 {
				line = line[:width - 5] + "..."
			}
			sb.WriteString(line + "\n")
		}
	}
	return sb.String()
}

func (m model) updateFileActivity(tool string, status string, detail string) model {
	if detail == "" {
		return m
	}
	
	action := "TOOL"
	switch tool {
	case "read_file":
		action = "READ"
	case "write_file":
		action = "WRITE"
	case "grep_search":
		action = "GREP"
	case "search_code":
		action = "SEARCH"
	case "run_command":
		action = "EXEC"
	}
	
	actStatus := "OK"
	switch status {
	case "start":
		actStatus = "ACTIVE"
	case "fail":
		actStatus = "ERROR"
	}
	
	displayPath := detail
	if strings.Contains(displayPath, "\\") || strings.Contains(displayPath, "/") {
		displayPath = filepath.Base(displayPath)
	}

	found := false
	for i, f := range m.activeFiles {
		if f.Path == displayPath {
			m.activeFiles[i].Status = actStatus
			m.activeFiles[i].Action = action
			found = true
			break
		}
	}
	
	if !found {
		// Newest at the top
		m.activeFiles = append([]fileActivity{{Path: displayPath, Action: action, Status: actStatus}}, m.activeFiles...)
		if len(m.activeFiles) > 6 {
			m.activeFiles = m.activeFiles[:6]
		}
	}
	return m
}

type axonConfig struct {
	Provider          string `json:"provider"`
	Model             string `json:"model"`
	AntigravityApiKey string `json:"antigravity_api_key"`
	OpenRouterApiKey  string `json:"openrouter_api_key"`
	CustomApiKey      string `json:"custom_api_key"`
	CustomBaseUrl     string `json:"custom_base_url"`
	OllamaBaseUrl     string `json:"ollama_base_url"`
}

func loadAxonConfig() (axonConfig, error) {
	appData := os.Getenv("APPDATA")
	configPath := filepath.Join(appData, "AXON", "config.json")
	data, err := os.ReadFile(configPath)
	if err != nil {
		return axonConfig{}, err
	}
	var cfg axonConfig
	err = json.Unmarshal(data, &cfg)
	return cfg, err
}

func makeDirectLLMRequest(prompt string, cfg axonConfig, p *tea.Program) {
	p.Send(wsStreamStartMsg{})
	
	var req *http.Request
	var err error
	
	if cfg.Provider == "antigravity" || cfg.Provider == "gemini" {
		modelName := cfg.Model
		if strings.Contains(modelName, "/") {
			parts := strings.Split(modelName, "/")
			modelName = parts[len(parts)-1]
		}
		if modelName == "" {
			modelName = "gemini-2.5-flash"
		}
		
		urlStr := fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models/%s:streamGenerateContent?key=%s", modelName, cfg.AntigravityApiKey)
		
		bodyMap := map[string]interface{}{
			"contents": []interface{}{
				map[string]interface{}{
					"parts": []interface{}{
						map[string]interface{}{
							"text": prompt,
						},
					},
				},
			},
		}
		bodyBytes, _ := json.Marshal(bodyMap)
		req, err = http.NewRequest("POST", urlStr, bytes.NewBuffer(bodyBytes))
		if err != nil {
			p.Send(wsErrorMsg{err: err.Error()})
			return
		}
		req.Header.Set("Content-Type", "application/json")
	} else if cfg.Provider == "openrouter" {
		urlStr := "https://openrouter.ai/api/v1/chat/completions"
		bodyMap := map[string]interface{}{
			"model": cfg.Model,
			"stream": true,
			"messages": []interface{}{
				map[string]interface{}{
					"role": "user",
					"content": prompt,
				},
			},
		}
		bodyBytes, _ := json.Marshal(bodyMap)
		req, err = http.NewRequest("POST", urlStr, bytes.NewBuffer(bodyBytes))
		if err != nil {
			p.Send(wsErrorMsg{err: err.Error()})
			return
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer " + cfg.OpenRouterApiKey)
	} else {
		baseUrl := cfg.OllamaBaseUrl
		if cfg.Provider == "custom" {
			baseUrl = cfg.CustomBaseUrl
		}
		if baseUrl == "" {
			baseUrl = "http://127.0.0.1:11434/v1"
		}
		urlStr := fmt.Sprintf("%s/chat/completions", strings.TrimSuffix(baseUrl, "/"))
		bodyMap := map[string]interface{}{
			"model": cfg.Model,
			"stream": true,
			"messages": []interface{}{
				map[string]interface{}{
					"role": "user",
					"content": prompt,
				},
			},
		}
		bodyBytes, _ := json.Marshal(bodyMap)
		req, err = http.NewRequest("POST", urlStr, bytes.NewBuffer(bodyBytes))
		if err != nil {
			p.Send(wsErrorMsg{err: err.Error()})
			return
		}
		req.Header.Set("Content-Type", "application/json")
		if cfg.Provider == "custom" && cfg.CustomApiKey != "" {
			req.Header.Set("Authorization", "Bearer " + cfg.CustomApiKey)
		}
	}
	
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		p.Send(wsErrorMsg{err: err.Error()})
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		p.Send(wsErrorMsg{err: fmt.Sprintf("API returned status %d", resp.StatusCode)})
		return
	}
	
	scanner := bufio.NewScanner(resp.Body)
	var accumulatedText strings.Builder
	var startTime time.Time
	tokenCount := 0

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		
		if cfg.Provider == "antigravity" || cfg.Provider == "gemini" {
			cleanJson := line
			if strings.HasPrefix(cleanJson, "[") {
				cleanJson = cleanJson[1:]
			}
			if strings.HasPrefix(cleanJson, ",") {
				cleanJson = cleanJson[1:]
			}
			if strings.HasSuffix(cleanJson, "]") {
				cleanJson = cleanJson[:len(cleanJson)-1]
			}
			cleanJson = strings.TrimSpace(cleanJson)
			if cleanJson == "" {
				continue
			}
			
			var geminiResp struct {
				Candidates []struct {
					Content struct {
						Parts []struct {
							Text string `json:"text"`
						} `json:"parts"`
					} `json:"content"`
				} `json:"candidates"`
			}
			if err := json.Unmarshal([]byte(cleanJson), &geminiResp); err == nil {
				if len(geminiResp.Candidates) > 0 && len(geminiResp.Candidates[0].Content.Parts) > 0 {
					txt := geminiResp.Candidates[0].Content.Parts[0].Text
					if txt != "" {
						if tokenCount == 0 {
							startTime = time.Now()
						}
						tokenCount++
						accumulatedText.WriteString(txt)
						p.Send(wsStreamDeltaMsg{delta: txt})
					}
				}
			}
		} else {
			if !strings.HasPrefix(line, "data:") {
				continue
			}
			dataContent := strings.TrimSpace(line[5:])
			if dataContent == "[DONE]" {
				break
			}
			
			var openAiResp struct {
				Choices []struct {
					Delta struct {
						Content string `json:"content"`
					} `json:"delta"`
				} `json:"choices"`
			}
			if err := json.Unmarshal([]byte(dataContent), &openAiResp); err == nil {
				if len(openAiResp.Choices) > 0 {
					txt := openAiResp.Choices[0].Delta.Content
					if txt != "" {
						if tokenCount == 0 {
							startTime = time.Now()
						}
						tokenCount++
						accumulatedText.WriteString(txt)
						p.Send(wsStreamDeltaMsg{delta: txt})
					}
				}
			}
		}
	}
	
	if tokenCount > 0 {
		duration := time.Since(startTime)
		tps := 0.0
		if duration.Seconds() > 0 {
			tps = float64(tokenCount) / duration.Seconds()
		}
		cost := float64(tokenCount) * 0.000002
		statsString := fmt.Sprintf("\n\n*[Speed: %.1f t/s | Tokens: %d | Cost: ~$%.5f]*", tps, tokenCount, cost)
		accumulatedText.WriteString(statsString)
	}
	
	p.Send(wsStreamEndMsg{text: accumulatedText.String()})
}

func (m model) saveSession() {
	userMsgs := 0
	var firstUserText string
	for _, msg := range m.messages {
		if msg.Type == 0 { // msgUser
			userMsgs++
			if firstUserText == "" {
				firstUserText = msg.Content
			}
		}
	}
	if userMsgs == 0 {
		return
	}

	appData := os.Getenv("APPDATA")
	if appData == "" {
		appData = filepath.Join(os.Getenv("USERPROFILE"), "AppData", "Roaming")
	}
	sessionsDir := filepath.Join(appData, "AXON", "sessions")
	_ = os.MkdirAll(sessionsDir, 0755)

	sessionID := ""
	const chars = "abcdef0123456789"
	b := make([]byte, 12)
	for i := range b {
		b[i] = chars[rand.Intn(len(chars))]
	}
	sessionID = string(b)

	title := firstUserText
	if len(title) > 80 {
		title = title[:80]
	}
	if title == "" {
		title = "Untitled Shard Session"
	}

	type jsonMeta struct {
		ID           string  `json:"id"`
		Title        string  `json:"title"`
		Model        string  `json:"model"`
		UpdatedAt    string  `json:"updated_at"`
		MessageCount int     `json:"message_count"`
		Tokens       int     `json:"tokens"`
	}

	type jsonMsg struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	}

	type sessionPayload struct {
		Meta     jsonMeta  `json:"meta"`
		Messages []jsonMsg `json:"messages"`
	}

	payload := sessionPayload{
		Meta: jsonMeta{
			ID:           sessionID,
			Title:        title,
			Model:        m.currentModel,
			UpdatedAt:    time.Now().UTC().Format(time.RFC3339),
			MessageCount: len(m.messages),
			Tokens:       m.totalTokens,
		},
		Messages: []jsonMsg{},
	}

	for _, msg := range m.messages {
		role := "assistant"
		content := msg.Content
		if msg.Type == 0 { // msgUser
			role = "user"
		} else if msg.Type == 2 { // msgTool
			role = "system"
			content = fmt.Sprintf("[TOOL %s (%s): %s]", msg.ToolName, msg.ToolStatus, msg.ToolDetail)
		} else if msg.Type == 3 { // msgThinking
			role = "assistant"
			content = "<thinking>\n" + msg.Content + "\n</thinking>"
		}
		payload.Messages = append(payload.Messages, jsonMsg{
			Role:    role,
			Content: content,
		})
	}

	filePath := filepath.Join(sessionsDir, sessionID+".json")
	fileBytes, err := json.MarshalIndent(payload, "", "  ")
	if err == nil {
		_ = os.WriteFile(filePath, fileBytes, 0644)
		fmt.Printf("\n[session] Chat history saved as %s.json\n", sessionID)
	}
}
