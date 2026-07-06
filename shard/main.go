package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/gorilla/websocket"
)

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

type model struct {
	conn                *websocket.Conn
	textInput           textinput.Model
	viewport            viewport.Model
	messages            []chatMessage
	currentMsg          strings.Builder
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
	totalTokens         int
	totalCost           float64
	splitPanes          bool
	expandedThinking    bool
	tickCount           int
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
         /\
        /  \
       / /\ \
      / /  \ \
     ▐ ▐ █ ▌ ▌
      \ \  / /
       \ \/ /
        \  /
         \/
`
		mascotColor = "#ff3333"
	}

	urlStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#38bdf8")).Underline(true)
	panelURL := urlStyle.Render("http://127.0.0.1:3000")

	mascotText := fmt.Sprintf(" Welcome to AXON Shard!\n I'm your agentic companion.\n Let's build something awesome!\n\n Control Panel: %s", panelURL)

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
			case tea.KeyTab, tea.KeyDown:
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

			// Send to websocket
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
		m.currentMsg.Reset()
		m.messages = append(m.messages, chatMessage{
			Type:    msgAxonText,
			Content: "",
		})
		m.viewport.SetContent(m.renderMessages())
		m.viewport.GotoBottom()

	case wsStreamDeltaMsg:
		m.tickCount++
		m.currentMsg.WriteString(msg.delta)
		for i := len(m.messages) - 1; i >= 0; i-- {
			if m.messages[i].Type == msgAxonText {
				m.messages[i].Content = m.currentMsg.String()
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
		hint := fmt.Sprintf(" ... (%d more, use Up/Down/Tab to scroll) ...", len(m.filteredSuggestions)-maxVisible)
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

	if _, err := p.Run(); err != nil {
		log.Fatal(err)
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

	body := fmt.Sprintf("\n%s\n\nStatus: %s\n\n· auto-approves runs\n· auto-writes files\n· safe approval bridge\n· F5 to collapse panels", header, statusLabel)
	return body
}

func (m model) renderTelemetryStatus(width int, height int) string {
	header := lipgloss.NewStyle().Foreground(accentColor).Bold(true).Render("Telemetry Logs")
	costStr := fmt.Sprintf("Session Cost:   $%.4f", m.totalCost)
	tokensStr := fmt.Sprintf("Session Tokens: %d", m.totalTokens)

	body := fmt.Sprintf("\n%s\n\n%s\n%s\n\n· status: nominal\n· websocket: active\n· latency: <45ms", header, costStr, tokensStr)
	return body
}
