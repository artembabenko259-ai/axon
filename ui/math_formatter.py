"""LaTeX mathematical formula formatter for AXON terminal views (uses Unicode math characters)."""

from __future__ import annotations

import re

# Greek lowercase letters mapping
LATEX_UNICODE = {
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

SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'x': 'ˣ', 'y': 'ʸ', 'i': 'ⁱ', 'j': 'ʲ'
}

SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'i': 'ᵢ',
    'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ', 's': 'ₛ', 't': 'ₜ'
}


def clean_expr(expr: str) -> str:
    # Replace basic commands
    for cmd, uni in LATEX_UNICODE.items():
        expr = expr.replace(cmd, uni)
    
    # Replace superscripts like ^{123} or ^2
    def replace_sup(m):
        content = m.group(1) or m.group(2)
        return "".join(SUPERSCRIPTS.get(c, c) for c in content)
    expr = re.sub(r"\^\{([^}]+)\}|\^([0-9a-zA-Z+\-()=])", replace_sup, expr)
    
    # Replace subscripts like _{abc} or _i
    def replace_sub(m):
        content = m.group(1) or m.group(2)
        return "".join(SUBSCRIPTS.get(c, c) for c in content)
    expr = re.sub(r"_\{([^}]+)\}|_([0-9a-zA-Z+\-()=])", replace_sub, expr)
    
    # Replace fractions like \frac{a}{b} -> (a)/(b)
    expr = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)", expr)
    # Replace square roots like \sqrt{x} -> √(x)
    expr = re.sub(r"\\sqrt\{([^}]+)\}", r"√(\1)", expr)
    
    return expr.strip()


def format_latex_math(text: str) -> str:
    # 1. Replace display blocks: $$ ... $$ or \[ ... \]
    def replace_display(match):
        formula_raw = match.group(1) or match.group(2) or ""
        formula = clean_expr(formula_raw)
        width = len(formula) + 6
        border_top = "┌" + "─" * (width - 2) + "┐"
        content    = f"│   {formula}   │"
        border_bot = "└" + "─" * (width - 2) + "┘"
        return f"\n{border_top}\n{content}\n{border_bot}\n"

    text = re.sub(r"\$\$(.*?)\$\$|\\\[(.*?)\\\]", replace_display, text, flags=re.DOTALL)

    # 2. Replace inline expressions: $ ... $ or \( ... \)
    def replace_inline(match):
        formula_raw = match.group(1) or match.group(2) or ""
        formula = clean_expr(formula_raw)
        return f" *{formula}* "

    text = re.sub(r"\$([^$]+)\$|\\\((.*?)\\\)", replace_inline, text)
    
    return text
