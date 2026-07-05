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
	Type    string `json:"type"`
	Content string `json:"content,omitempty"`
	Text    string `json:"text,omitempty"`
	Delta   string `json:"delta,omitempty"`
	Model   string `json:"model,omitempty"`
	Token   string `json:"token,omitempty"`
	Tool    string `json:"tool,omitempty"`
	Status  string `json:"status,omitempty"`
	Detail  string `json:"detail,omitempty"`
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

type command struct {
	Name        string
	Description string
}

var autocompleteCommands = []command{
	{"/help", "Show help and command guide"},
	{"/plan", "Create a task board and plan steps"},
	{"/multitask", "Run parallel sub-agents for a goal"},
	{"/delegate", "Assign a task to a specific sub-agent"},
	{"/commit", "Create a git commit of workspace changes"},
	{"/artifacts", "View or open generated files"},
	{"/clear", "Clear chat screen"},
	{"/exit", "Exit AXON Shard"},
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
}

func initialModel(conn *websocket.Conn) model {
	ti := textinput.New()
	ti.Placeholder = "Ask AXON anything... (type / for commands)"
	ti.Focus()
	ti.CharLimit = 4096
	ti.Prompt = " ❯ "
	ti.PromptStyle = lipgloss.NewStyle().Foreground(accentColor).Bold(true)

	vp := viewport.New(80, 20)
	vp.SetContent("[..] Connecting to AXON core bridge...")

	return model{
		conn:         conn,
		textInput:    ti,
		viewport:     vp,
		messages:     []chatMessage{},
		currentModel: "detecting...",
		status:       "CONNECTING",
		connected:    false,
	}
}

func (m model) getWelcomeMessage() string {
	crab := `
    (●)     (●)
     \ \___/ /
     / ◕   ◕ \
   (│    ◡    │)
    │ ──┬──┬── │
    /\  /\  /\
`
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

	crabBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderColor).
		Padding(1, 2).
		Foreground(lipgloss.Color("#f87171")). // Premium coral red crab
		Render(crab)

	mascotTextBox := lipgloss.NewStyle().
		Padding(2, 1).
		Foreground(textColor).
		Render(mascotText)

	mascotBlock := lipgloss.JoinHorizontal(lipgloss.Center, crabBox, mascotTextBox)

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
			formatted := formatLatexMath(msg.Content)
			sb.WriteString(fmt.Sprintf("\n✦ AXON:\n%s\n", formatted))
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
				m.textInput.SetValue(selected + " ")
				m.textInput.SetCursor(len(selected) + 1)
				m.showSuggestions = false
				return m, nil
			}
		}

		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
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

			// Send to websocket
			chatMsg := wsMsg{
				Type: "chat",
				Text: input,
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
			if strings.HasPrefix(val, "/") {
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
		if m.showSuggestions && len(m.filteredSuggestions) > 0 {
			viewportHeight -= (len(m.filteredSuggestions) + 2)
		}
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
	if m.showSuggestions && len(m.filteredSuggestions) > 0 {
		viewportHeight -= (len(m.filteredSuggestions) + 2)
	}
	if viewportHeight < 1 {
		viewportHeight = 1
	}
	if m.viewport.Height != viewportHeight {
		m.viewport.Height = viewportHeight
		m.viewport.GotoBottom()
	}

	return m, tea.Batch(cmds...)
}

func (m model) autocompleteView() string {
	if !m.showSuggestions || len(m.filteredSuggestions) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Foreground(borderColor).Render(" ┌" + strings.Repeat("─", m.width-6) + "┐") + "\n")

	for i, cmd := range m.filteredSuggestions {
		style := lipgloss.NewStyle().Padding(0, 2)
		if i == m.suggestionIdx {
			style = style.
				Background(lipgloss.Color("#262626")).
				Foreground(lipgloss.Color("#ffffff")).
				Bold(true)
		} else {
			style = style.Foreground(textColor)
		}

		cmdStr := fmt.Sprintf("%-12s  %s", cmd.Name, cmd.Description)
		if len(cmdStr) > m.width-10 {
			cmdStr = cmdStr[:m.width-13] + "..."
		}

		paddedLine := style.Render(fmt.Sprintf(" %-*s", m.width-8, cmdStr))
		sb.WriteString(paddedLine + "\n")
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

	// 2. Chat history viewport
	chatView := m.viewport.View()

	// 3. Autocomplete popup
	popup := m.autocompleteView()

	// 4. Border line
	borderLine := borderLineStyle.Render(strings.Repeat("─", m.width))

	// 5. Text input field
	input := m.textInput.View()

	// 6. Status bar
	statusText := fmt.Sprintf("  Status: %s   │   Ctrl+C to quit", m.status)
	if m.width > 80 {
		statusText = fmt.Sprintf("  Status: %s   │   Zenith Panel: http://127.0.0.1:3000   │   Ctrl+C to quit", m.status)
	}
	footer := statusStyle.Render(statusText)

	if popup != "" {
		return lipgloss.JoinVertical(
			lipgloss.Left,
			header,
			chatView,
			popup,
			borderLine,
			input,
			footer,
		)
	}

	return lipgloss.JoinVertical(
		lipgloss.Left,
		header,
		chatView,
		borderLine,
		input,
		footer,
	)
}

func main() {
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
