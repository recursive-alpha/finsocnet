import os
import xml.etree.ElementTree as ET

os.makedirs("assets/logos", exist_ok=True)

# Helper for standalone avatar wrap
def wrap_avatar(inner_svg, title, subtitle, grad_stops=None):
    if not grad_stops:
        grad_stops = '<stop offset="0%" stop-color="#00FFA3"/><stop offset="50%" stop-color="#00D2FF"/><stop offset="100%" stop-color="#7928CA"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#07090E"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      {grad_stops}
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  <rect width="500" height="500" rx="90" fill="url(#bg)"/>
  <circle cx="250" cy="230" r="190" fill="none" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="3,6"/>
  {inner_svg}
  <text x="250" y="420" text-anchor="middle" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="22" letter-spacing="4">{title}</text>
  <text x="250" y="444" text-anchor="middle" fill="#00FFA3" font-family="monospace" font-weight="600" font-size="11" letter-spacing="2">{subtitle}</text>
</svg>'''

logos = {}

# 05. The Möbius Alpha
m1 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Front and back twist ribbons of Mobius loop forming alpha -->
  <path d="M 90,-55 C 40,-55 -10,-10 -35,25 C -55,55 -90,75 -125,75 C -165,75 -190,45 -190,5 C -190,-35 -160,-65 -120,-65 C -75,-65 -35,-25 -10,25 C 15,70 50,75 90,75" 
        fill="none" stroke="url(#grad)" stroke-width="18" stroke-linecap="round"/>
  <path d="M 90,-55 C 50,-55 20,-20 0,15 C -20,50 -55,75 -90,75" 
        fill="none" stroke="#07090E" stroke-width="6" stroke-dasharray="10,6"/>
  <!-- Twist intersection node -->
  <polygon points="-12,-5 12,5 0,25" fill="#00FFA3"/>
  <circle cx="-120" cy="5" r="14" fill="none" stroke="#00FFA3" stroke-width="2"/>
  <text x="-120" y="9" text-anchor="middle" fill="#00FFA3" font-family="monospace" font-size="12" font-weight="bold">∞</text>
</g>
'''
logos["05_mobius_alpha"] = (m1, "RECURSIVE ALPHA", "// MÖBIUS LOOP TOPOLOGY")

# 06. The Decompiled Black Box
m2 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Outer Decompiled Panels peeling back -->
  <!-- Top Panel -->
  <polygon points="0,-120 70,-80 0,-40 -70,-80" fill="none" stroke="#00D2FF" stroke-width="2" stroke-dasharray="4,4"/>
  <!-- Left Panel -->
  <polygon points="-120,-40 -80,-20 -80,60 -120,40" fill="none" stroke="#334155" stroke-width="2"/>
  <!-- Right Panel -->
  <polygon points="120,-40 80,-20 80,60 120,40" fill="none" stroke="#334155" stroke-width="2"/>
  <!-- Exploded Reverse Vector Arrows -->
  <line x1="-70" y1="-80" x2="-95" y2="-95" stroke="#00FFA3" stroke-width="2"/>
  <line x1="70" y1="-80" x2="95" y2="-95" stroke="#00FFA3" stroke-width="2"/>
  <line x1="0" y1="90" x2="0" y2="115" stroke="#00FFA3" stroke-width="2"/>
  
  <!-- Glowing Core: The Alpha Key Extracted -->
  <circle cx="0" cy="10" r="45" fill="#0B132B" stroke="#00FFA3" stroke-width="2"/>
  <path d="M 22,-6 C 10,-6 -2,12 -12,24 C -20,24 -26,14 -26,4 C -26,-6 -18,-14 -8,-14 C 2,-14 12,-4 18,10 C 22,18 28,22 34,22" 
        fill="none" stroke="url(#grad)" stroke-width="7" stroke-linecap="round"/>
</g>
'''
logos["06_decompiled_blackbox"] = (m2, "RECURSIVE ALPHA", "// BLACK-BOX DECOMPILER")

# 07. The Recursive Call-Stack
m3 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Nested Call Stack Frames -->
  <rect x="-110" y="-100" width="220" height="200" rx="14" fill="none" stroke="#1E293B" stroke-width="2"/>
  <text x="-95" y="-80" fill="#334155" font-family="monospace" font-size="11">frame_0: main()</text>
  
  <rect x="-80" y="-70" width="160" height="150" rx="10" fill="none" stroke="#334155" stroke-width="2"/>
  <text x="-68" y="-52" fill="#64748B" font-family="monospace" font-size="10">frame_1: decompile()</text>

  <rect x="-50" y="-40" width="100" height="100" rx="8" fill="none" stroke="#00D2FF" stroke-width="2"/>
  <text x="-38" y="-25" fill="#00D2FF" font-family="monospace" font-size="9">frame_2: solve()</text>

  <!-- Core Alpha in inner frame -->
  <path d="M 16,-8 C 6,-8 -4,6 -10,16 C -16,16 -20,8 -20,0 C -20,-8 -14,-14 -6,-14 C 2,-14 8,-6 14,8 C 18,14 24,18 28,18" 
        fill="none" stroke="#00FFA3" stroke-width="5" stroke-linecap="round"/>
  <!-- Return Arrow down-up -->
  <polyline points="-35,30 -35,50 35,50 35,30" fill="none" stroke="#00FFA3" stroke-width="2" stroke-linecap="round"/>
  <polyline points="-30,36 -35,30 -40,36" fill="none" stroke="#00FFA3" stroke-width="2"/>
</g>
'''
logos["07_recursive_stack"] = (m3, "RECURSIVE ALPHA", "// RECURSIVE CALL STACK")

# 08. The Delta-Alpha Hedge
m4 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Quant Delta Triangle (Hedge Neutrality) -->
  <polygon points="0,-115 110,65 -110,65" fill="none" stroke="#1E293B" stroke-width="3"/>
  <polygon points="0,-95 90,50 -90,50" fill="none" stroke="#00D2FF" stroke-width="2" opacity="0.4"/>
  
  <!-- Interlocking Reverse Alpha Loop -->
  <path d="M 60,-15 C 30,-15 0,20 -25,48 C -45,48 -60,32 -60,12 C -60,-10 -42,-26 -18,-26 C 8,-26 32,-4 46,24 C 54,40 68,48 84,48" 
        fill="none" stroke="url(#grad)" stroke-width="9" stroke-linecap="round"/>
  
  <!-- Balance scale horizon tick -->
  <line x1="-125" y1="65" x2="125" y2="65" stroke="#00FFA3" stroke-width="3" stroke-linecap="round"/>
  <circle cx="0" cy="-115" r="5" fill="#00FFA3"/>
  <circle cx="-110" cy="65" r="5" fill="#00D2FF"/>
  <circle cx="110" cy="65" r="5" fill="#7928CA"/>
</g>
'''
logos["08_delta_hedge_alpha"] = (m4, "RECURSIVE ALPHA", "// DELTA-NEUTRAL HEDGE")

# 09. The AST Graph & Alpha Node
m5 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Branching AST connections forming an alpha flow -->
  <line x1="0" y1="-90" x2="-65" y2="-20" stroke="#334155" stroke-width="2"/>
  <line x1="0" y1="-90" x2="65" y2="-20" stroke="#334155" stroke-width="2"/>
  <line x1="-65" y1="-20" x2="-90" y2="55" stroke="#334155" stroke-width="2"/>
  <line x1="-65" y1="-20" x2="-25" y2="55" stroke="#334155" stroke-width="2"/>
  <line x1="65" y1="-20" x2="35" y2="55" stroke="#334155" stroke-width="2"/>
  <line x1="65" y1="-20" x2="95" y2="55" stroke="#334155" stroke-width="2"/>
  
  <!-- Cyclic Reverse Feedback Loop (Graph Recursion) -->
  <path d="M -90,55 C -60,95 60,95 95,55 C 120,20 80,-70 0,-90" 
        fill="none" stroke="#00FFA3" stroke-width="3" stroke-dasharray="6,4" stroke-linecap="round"/>

  <!-- Graph Nodes -->
  <circle cx="0" cy="-90" r="10" fill="#07090E" stroke="#00FFA3" stroke-width="2.5"/>
  <circle cx="-65" cy="-20" r="8" fill="#07090E" stroke="#00D2FF" stroke-width="2"/>
  <circle cx="65" cy="-20" r="8" fill="#07090E" stroke="#00D2FF" stroke-width="2"/>
  <circle cx="-90" cy="55" r="7" fill="#07090E" stroke="#7928CA" stroke-width="2"/>
  <circle cx="-25" cy="55" r="7" fill="#07090E" stroke="#7928CA" stroke-width="2"/>
  <circle cx="35" cy="55" r="7" fill="#07090E" stroke="#7928CA" stroke-width="2"/>
  <circle cx="95" cy="55" r="7" fill="#07090E" stroke="#7928CA" stroke-width="2"/>
  
  <!-- Alpha glyph in root node -->
  <text x="0" y="-86" text-anchor="middle" fill="#00FFA3" font-family="monospace" font-size="11" font-weight="bold">α</text>
</g>
'''
logos["09_ast_graph_alpha"] = (m5, "RECURSIVE ALPHA", "// AST SYNTAX GRAPH")

# 10. The Penrose Impossible Loop
m6 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Isometric Impossible Alpha loop -->
  <path d="M 0,-100 L 25,-85 L -35,20 L 70,20 L 85,45 L -85,45 L -85,25 Z" fill="#00FFA3" opacity="0.9"/>
  <path d="M 85,45 L 60,60 L -60,60 L -35,20 L -85,25 L -100,0 L 0,-100 Z" fill="#00D2FF" opacity="0.75"/>
  <path d="M 25,-85 L 85,20 L 85,45 L 70,20 L -35,20 L 0,-40 Z" fill="#7928CA" opacity="0.6"/>
  <!-- Impossible optical intersection -->
  <circle cx="0" cy="0" r="16" fill="#07090E" stroke="#00FFA3" stroke-width="2"/>
  <text x="0" y="5" text-anchor="middle" fill="#FFFFFF" font-family="monospace" font-size="12" font-weight="bold">α</text>
</g>
'''
logos["10_penrose_loop"] = (m6, "RECURSIVE ALPHA", "// IMPOSSIBLE PENROSE EDGE")

# 11. The Reversal Terminal Glyphs
m7 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Brutalist Monospace Terminal Framing -->
  <text x="-95" y="-55" fill="#334155" font-family="monospace" font-size="34" font-weight="bold">&lt;&lt;</text>
  <text x="55" y="-55" fill="#334155" font-family="monospace" font-size="34" font-weight="bold">&gt;&gt;</text>
  <text x="-95" y="75" fill="#334155" font-family="monospace" font-size="34" font-weight="bold">[</text>
  <text x="75" y="75" fill="#334155" font-family="monospace" font-size="34" font-weight="bold">]</text>

  <!-- Massive Bold Cyber Alpha -->
  <path d="M 45,-25 C 20,-25 -5,12 -25,40 C -45,40 -60,24 -60,4 C -60,-18 -42,-34 -18,-34 C 8,-34 30,-12 44,18 C 52,34 66,42 80,42" 
        fill="none" stroke="url(#grad)" stroke-width="12" stroke-linecap="round"/>
  <!-- Cursor block -->
  <rect x="75" y="10" width="8" height="20" fill="#00FFA3"/>
  <text x="-15" y="-45" text-anchor="middle" fill="#00FFA3" font-family="monospace" font-size="12">// RE_DISASM</text>
</g>
'''
logos["11_reversal_terminal"] = (m7, "RECURSIVE ALPHA", "// MONOSPACE TERMINAL")

# 12. The Depth-of-Market Spiral
m8 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Stepped Order Book Bid/Ask Bars spiraling into Alpha -->
  <!-- Left Bid Steps (Green) -->
  <rect x="-95" y="-50" width="30" height="8" rx="2" fill="#00FFA3" opacity="0.3"/>
  <rect x="-80" y="-35" width="35" height="8" rx="2" fill="#00FFA3" opacity="0.5"/>
  <rect x="-70" y="-20" width="45" height="8" rx="2" fill="#00FFA3" opacity="0.7"/>
  <rect x="-60" y="-5" width="55" height="8" rx="2" fill="#00FFA3" opacity="0.9"/>
  <!-- Right Ask Steps (Cyan/Violet) -->
  <rect x="25" y="5" width="55" height="8" rx="2" fill="#00D2FF" opacity="0.9"/>
  <rect x="25" y="20" width="45" height="8" rx="2" fill="#00D2FF" opacity="0.7"/>
  <rect x="25" y="35" width="35" height="8" rx="2" fill="#00D2FF" opacity="0.5"/>
  <rect x="25" y="50" width="25" height="8" rx="2" fill="#00D2FF" opacity="0.3"/>
  
  <!-- Center Microstructure Alpha Crosshair -->
  <circle cx="0" cy="0" r="50" fill="none" stroke="#1E293B" stroke-width="2"/>
  <line x1="-65" y1="0" x2="65" y2="0" stroke="#334155" stroke-width="1.5" stroke-dasharray="2,4"/>
  <line x1="0" y1="-65" x2="0" y2="65" stroke="#334155" stroke-width="1.5" stroke-dasharray="2,4"/>
  <path d="M 28,-14 C 14,-14 0,6 -12,24 C -22,24 -28,14 -28,4 C -28,-8 -20,-18 -8,-18 C 4,-18 16,-4 22,12 C 26,20 32,24 38,24" 
        fill="none" stroke="url(#grad)" stroke-width="6" stroke-linecap="round"/>
</g>
'''
logos["12_depth_spiral"] = (m8, "RECURSIVE ALPHA", "// ORDER BOOK MICROSTRUCTURE")

# 13. The Fractal Candlestick
m9 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- Outer Master Candlestick -->
  <line x1="0" y1="-110" x2="0" y2="100" stroke="#1E293B" stroke-width="3"/>
  <rect x="-65" y="-55" width="130" height="110" rx="6" fill="#0B132B" stroke="#00D2FF" stroke-width="2"/>

  <!-- Inner Recursive Candlesticks forming the Alpha path -->
  <g transform="translate(-45, 0)">
    <!-- Loop left -->
    <line x1="0" y1="-30" x2="0" y2="30" stroke="#00FFA3" stroke-width="1.5"/>
    <rect x="-6" y="-15" width="12" height="30" rx="2" fill="#00FFA3"/>
  </g>
  <g transform="translate(-15, -25)">
    <line x1="0" y1="-20" x2="0" y2="20" stroke="#00FFA3" stroke-width="1.5"/>
    <rect x="-5" y="-10" width="10" height="20" rx="2" fill="#00FFA3"/>
  </g>
  <g transform="translate(15, 25)">
    <line x1="0" y1="-20" x2="0" y2="20" stroke="#00FFA3" stroke-width="1.5"/>
    <rect x="-5" y="-10" width="10" height="20" rx="2" fill="#00FFA3"/>
  </g>
  <g transform="translate(45, -15)">
    <line x1="0" y1="-35" x2="0" y2="35" stroke="#00D2FF" stroke-width="1.5"/>
    <rect x="-6" y="-18" width="12" height="36" rx="2" fill="#00D2FF"/>
  </g>

  <!-- Alpha connecting line across the bars -->
  <path d="M 45,-15 C 25,-15 5,10 -15,25 C -30,25 -45,15 -45,0 C -45,-15 -30,-25 -15,-25 C 5,-25 25,0 45,20" 
        fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-dasharray="4,3" stroke-linecap="round"/>
</g>
'''
logos["13_fractal_candlestick"] = (m9, "RECURSIVE ALPHA", "// MULTI-TIMEFRAME FRACTAL")

# 14. The Tensor Lattice
m10 = '''
<g filter="url(#glow)" transform="translate(250, 225)">
  <!-- 4x4 Neural Weight Matrix Grid -->
  <g stroke="#1E293B" stroke-width="1.5">
    <line x1="-75" y1="-75" x2="75" y2="-75"/>
    <line x1="-75" y1="-25" x2="75" y2="-25"/>
    <line x1="-75" y1="25" x2="75" y2="25"/>
    <line x1="-75" y1="75" x2="75" y2="75"/>

    <line x1="-75" y1="-75" x2="-75" y2="75"/>
    <line x1="-25" y1="-75" x2="-25" y2="75"/>
    <line x1="25" y1="-75" x2="25" y2="75"/>
    <line x1="75" y1="-75" x2="75" y2="75"/>
  </g>

  <!-- Activated Alpha Path through the Tensor -->
  <path d="M 75,-25 L 25,-25 L -25,25 L -75,25 L -75,-25 L -25,-25 L 25,25 L 75,75" 
        fill="none" stroke="url(#grad)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>

  <!-- Glowing Attention / Weight Activation Nodes -->
  <circle cx="75" cy="-25" r="5" fill="#00FFA3"/>
  <circle cx="25" cy="-25" r="5" fill="#00FFA3"/>
  <circle cx="-25" cy="25" r="6" fill="#00D2FF"/>
  <circle cx="-75" cy="25" r="5" fill="#00D2FF"/>
  <circle cx="-75" cy="-25" r="5" fill="#7928CA"/>
  <circle cx="-25" cy="-25" r="6" fill="#7928CA"/>
  <circle cx="25" cy="25" r="6" fill="#00FFA3"/>
  <circle cx="75" cy="75" r="5" fill="#00FFA3"/>
</g>
'''
logos["14_tensor_lattice"] = (m10, "RECURSIVE ALPHA", "// NEURAL TENSOR LATTICE")

# Generate all 10
for name, (inner, title, sub) in logos.items():
    content = wrap_avatar(inner, title, sub)
    ET.fromstring(content) # validate XML
    filepath = f"assets/logos/{name}.svg"
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Generated {filepath}")

print("All 10 non-animal SVG logos created and validated successfully!")
