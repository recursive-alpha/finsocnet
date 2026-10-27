import os

os.makedirs("assets/logos", exist_ok=True)

# 1. Candidate 1: The Cyber-Ouroboros (Serpent Alpha)
c1_ouroboros = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06090F"/>
      <stop offset="100%" stop-color="#0E1626"/>
    </linearGradient>
    <linearGradient id="alpha-grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00FFA3"/>
      <stop offset="50%" stop-color="#00D2FF"/>
      <stop offset="100%" stop-color="#7928CA"/>
    </linearGradient>
    <filter id="glow1" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <rect width="500" height="500" rx="90" fill="url(#bg1)"/>
  
  <!-- Quant Polar Grid -->
  <circle cx="250" cy="235" r="190" fill="none" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="3,6"/>
  <circle cx="250" cy="235" r="150" fill="none" stroke="#334155" stroke-width="1" stroke-dasharray="2,6" opacity="0.5"/>
  <circle cx="180" cy="235" r="75" fill="none" stroke="#00FFA3" stroke-width="1" stroke-opacity="0.15"/>
  <line x1="250" y1="35" x2="250" y2="60" stroke="#00FFA3" stroke-width="2" opacity="0.6"/>
  <line x1="250" y1="410" x2="250" y2="435" stroke="#00FFA3" stroke-width="2" opacity="0.6"/>
  <line x1="45" y1="235" x2="70" y2="235" stroke="#00FFA3" stroke-width="2" opacity="0.6"/>
  <line x1="430" y1="235" x2="455" y2="235" stroke="#00FFA3" stroke-width="2" opacity="0.6"/>

  <!-- Candlestick micro-ticks -->
  <g opacity="0.2">
    <line x1="90" y1="180" x2="90" y2="260" stroke="#00FFA3" stroke-width="1"/>
    <rect x="87" y="200" width="6" height="35" fill="#00FFA3"/>
    <line x1="410" y1="190" x2="410" y2="280" stroke="#00D2FF" stroke-width="1"/>
    <rect x="407" y="215" width="6" height="40" fill="#00D2FF"/>
  </g>

  <!-- Alpha Ouroboros Body -->
  <g filter="url(#glow1)">
    <path d="M 360,150 
             C 310,150 265,200 240,235 
             C 210,275 170,320 115,320 
             C 65,320 35,280 35,235 
             C 35,190 65,150 115,150 
             C 170,150 210,195 240,235 
             C 265,270 310,320 360,320 
             C 400,320 425,295 430,255 
             C 435,215 410,180 375,160 Z"
          fill="none" stroke="url(#alpha-grad1)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- Reverse Segments / Opcode Scale dashes -->
  <path d="M 350,158 
           C 305,158 262,204 238,235 
           C 212,271 172,312 120,312 
           C 72,312 45,277 45,235 
           C 45,193 72,158 120,158 
           C 172,158 212,199 238,235 
           C 262,267 305,312 350,312"
        fill="none" stroke="#06090F" stroke-width="5" stroke-dasharray="12,8"/>

  <!-- Serpent Head (Top Right looping to reverse strike) -->
  <g transform="translate(365, 150) rotate(-28)">
    <polygon points="0,-15 46,-5 60,0 46,5 0,15 -10,0" fill="#00FFA3"/>
    <polygon points="5,-9 36,-3 44,0 36,3 5,9 0,0" fill="#06090F"/>
    <circle cx="22" cy="-3" r="3" fill="#FFFFFF"/>
    <path d="M 60,0 L 76,0 M 76,0 L 88,-7 M 76,0 L 88,7" stroke="#00FFA3" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  </g>

  <!-- Reverse Loop Icon & Disassembly Hex in center -->
  <g fill="#00D2FF" opacity="0.85">
    <circle cx="115" cy="235" r="32" fill="none" stroke="#00FFA3" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.4"/>
    <path d="M 106,219 L 124,219 A 16 16 0 1 1 103,240" fill="none" stroke="#00FFA3" stroke-width="2.2" stroke-linecap="round"/>
    <polyline points="111,213 105,219 111,225" fill="none" stroke="#00FFA3" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="115" y="240" text-anchor="middle" fill="#FFFFFF" font-size="12" font-family="monospace" font-weight="bold">0xα</text>
  </g>

  <!-- Typography -->
  <text x="250" y="420" text-anchor="middle" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="22" letter-spacing="4">RECURSIVE ALPHA</text>
  <text x="250" y="442" text-anchor="middle" fill="#00FFA3" font-family="monospace" font-weight="600" font-size="11" letter-spacing="2">// REVERSE QUANT HEDGE</text>
</svg>'''

# 2. Candidate 2: The Corvid Disassembler (Raven Alpha)
c2_corvid = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#08070D"/>
      <stop offset="100%" stop-color="#141122"/>
    </linearGradient>
    <linearGradient id="corvid-violet" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6"/>
      <stop offset="50%" stop-color="#6366F1"/>
      <stop offset="100%" stop-color="#00FFA3"/>
    </linearGradient>
    <linearGradient id="wing-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#2E1065"/>
      <stop offset="100%" stop-color="#8B5CF6"/>
    </linearGradient>
    <filter id="glow2" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <rect width="500" height="500" rx="90" fill="url(#bg2)"/>
  
  <!-- Outer Hexagonal Reticle for Reverse Engineering Shield -->
  <polygon points="250,35 430,135 430,345 250,445 70,345 70,135" fill="none" stroke="#1E1B2E" stroke-width="2"/>
  <polygon points="250,55 410,145 410,335 250,425 90,335 90,145" fill="none" stroke="#8B5CF6" stroke-width="1" stroke-dasharray="4,8" opacity="0.3"/>

  <!-- Raven Head and Beak Profile (Disassembling the Alpha lock) -->
  <g transform="translate(140, 90)">
    <!-- Crown / Crest -->
    <polygon points="110,30 140,45 130,20 160,35 150,10 180,25 150,60 110,65" fill="#A78BFA"/>
    <!-- Head Facets -->
    <polygon points="110,65 150,60 170,95 125,105" fill="#7C3AED"/>
    <polygon points="170,95 210,100 175,115 125,105" fill="#6D28D9"/>
    <!-- Sharp Beak grabbing the Alpha key -->
    <polygon points="210,100 270,115 175,122" fill="#00FFA3"/>
    <polygon points="210,122 255,122 175,135" fill="#059669"/>
    <!-- Cyber Eye (Reverse Target Lock) -->
    <circle cx="160" cy="90" r="5" fill="#00FFA3"/>
    <circle cx="160" cy="90" r="2" fill="#FFFFFF"/>
  </g>

  <!-- Stepped Wing Feathers: Shape of Decompiler AST / Reverse Chevrons <<< -->
  <g opacity="0.9">
    <!-- Feather Tier 1 (Outer Chevron) -->
    <polygon points="150,210 210,210 120,310 80,310" fill="#4C1D95"/>
    <polygon points="170,225 225,225 155,305 115,305" fill="#5B21B6"/>
    <!-- Feather Tier 2 (Mid Chevron) -->
    <polygon points="190,240 240,240 190,300 150,300" fill="#6D28D9"/>
    <!-- Feather Tier 3 (Inner Chevron) -->
    <polygon points="210,255 255,255 225,295 190,295" fill="#7C3AED"/>
  </g>

  <!-- The Alpha Key Glyph: Glowing and Deconstructed -->
  <g filter="url(#glow2)" transform="translate(310, 205)">
    <!-- Code Braces / Reverse Box enclosing Alpha -->
    <path d="M -30,-30 L -45,-30 L -45,30 L -30,30" fill="none" stroke="#8B5CF6" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M 30,-30 L 45,-30 L 45,30 L 30,30" fill="none" stroke="#8B5CF6" stroke-width="2.5" stroke-linecap="round"/>
    
    <!-- Greek Alpha Key -->
    <path d="M 25,-18 C 5,-18 -15,5 -28,25 M -28,25 C -42,25 -50,10 -50,-5 C -50,-20 -38,-30 -22,-30 C -2,-30 15,-10 28,12 C 34,22 42,28 50,28" 
          fill="none" stroke="#00FFA3" stroke-width="6" stroke-linecap="round"/>
    <circle cx="28" cy="12" r="3" fill="#FFFFFF"/>
  </g>

  <!-- Candlestick Claws gripping the lower support line -->
  <g stroke="#00FFA3" stroke-width="3" stroke-linecap="round">
    <line x1="230" y1="330" x2="225" y2="350"/>
    <line x1="240" y1="330" x2="242" y2="352"/>
    <line x1="250" y1="330" x2="258" y2="348"/>
    <!-- Support Trendline (Base of Hedge) -->
    <line x1="160" y1="352" x2="350" y2="352" stroke="#6D28D9" stroke-width="2"/>
  </g>

  <!-- Typography -->
  <text x="250" y="420" text-anchor="middle" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="22" letter-spacing="4">RECURSIVE ALPHA</text>
  <text x="250" y="442" text-anchor="middle" fill="#A78BFA" font-family="monospace" font-weight="600" font-size="11" letter-spacing="2">// CORVID DECOMPILER</text>
</svg>'''

# 3. Candidate 3: The Radar Owl (Nocturnal Microstructure Alpha)
c3_owl = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#050C14"/>
      <stop offset="100%" stop-color="#0A192F"/>
    </linearGradient>
    <linearGradient id="owl-cyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00FFA3"/>
      <stop offset="100%" stop-color="#00B8D9"/>
    </linearGradient>
    <linearGradient id="shield-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#0B132B"/>
    </linearGradient>
    <filter id="glow3" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <rect width="500" height="500" rx="90" fill="url(#bg3)"/>
  
  <!-- Outer Hedge Fund Shield Outline -->
  <path d="M 250,50 L 390,100 L 390,260 C 390,340 320,390 250,420 C 180,390 110,340 110,260 L 110,100 Z" 
        fill="none" stroke="#1E293B" stroke-width="2"/>
  <path d="M 250,65 L 375,110 L 375,255 C 375,325 315,370 250,398 C 185,370 125,325 125,255 L 125,110 Z" 
        fill="url(#shield-grad)" stroke="#00FFA3" stroke-width="1.2" stroke-dasharray="6,4" opacity="0.6"/>

  <!-- Owl Ear Tufts / Angular Terminal Brackets < > -->
  <polygon points="175,110 205,160 150,160" fill="#00FFA3" opacity="0.9"/>
  <polygon points="325,110 350,160 295,160" fill="#00FFA3" opacity="0.9"/>
  
  <!-- Owl Brow / Mask forming overarching Alpha Loop Span -->
  <path d="M 160,165 Q 250,195 340,165 L 320,200 Q 250,220 180,200 Z" fill="#0E2439" stroke="#00B8D9" stroke-width="2"/>

  <!-- Radar Eyes: Concentric Depth of Market (DoM) Rings with Crosshairs -->
  <!-- Left Eye -->
  <g transform="translate(195, 220)">
    <circle cx="0" cy="0" r="38" fill="#050C14" stroke="#1E3A5F" stroke-width="2"/>
    <circle cx="0" cy="0" r="28" fill="none" stroke="#00B8D9" stroke-width="1" stroke-dasharray="2,4"/>
    <circle cx="0" cy="0" r="18" fill="none" stroke="#00FFA3" stroke-width="1.5"/>
    <circle cx="0" cy="0" r="6" fill="#00FFA3"/>
    <circle cx="0" cy="0" r="2" fill="#FFFFFF"/>
    <!-- Radar Sweep lines -->
    <line x1="-38" y1="0" x2="38" y2="0" stroke="#00B8D9" stroke-width="1" opacity="0.4"/>
    <line x1="0" y1="-38" x2="0" y2="38" stroke="#00B8D9" stroke-width="1" opacity="0.4"/>
    <line x1="0" y1="0" x2="20" y2="-20" stroke="#00FFA3" stroke-width="1.5"/>
  </g>

  <!-- Right Eye (Mirrored with Greek Alpha Pupil) -->
  <g transform="translate(305, 220)">
    <circle cx="0" cy="0" r="38" fill="#050C14" stroke="#1E3A5F" stroke-width="2"/>
    <circle cx="0" cy="0" r="28" fill="none" stroke="#00B8D9" stroke-width="1" stroke-dasharray="2,4"/>
    <circle cx="0" cy="0" r="18" fill="none" stroke="#00FFA3" stroke-width="1.5"/>
    <circle cx="0" cy="0" r="6" fill="#00FFA3"/>
    <circle cx="0" cy="0" r="2" fill="#FFFFFF"/>
    <line x1="-38" y1="0" x2="38" y2="0" stroke="#00B8D9" stroke-width="1" opacity="0.4"/>
    <line x1="0" y1="-38" x2="0" y2="38" stroke="#00B8D9" stroke-width="1" opacity="0.4"/>
    <line x1="0" y1="0" x2="-20" y2="-20" stroke="#00FFA3" stroke-width="1.5"/>
  </g>

  <!-- Beak: Downward Execution Vector -->
  <polygon points="250,210 262,245 250,265 238,245" fill="#00FFA3"/>

  <!-- Chest Plumage: Cascading Candlesticks / Order Book Imbalance -->
  <g transform="translate(250, 285)" filter="url(#glow3)">
    <!-- Center Candlestick Spine -->
    <line x1="0" y1="-10" x2="0" y2="65" stroke="#00FFA3" stroke-width="2"/>
    <rect x="-8" y="5" width="16" height="35" rx="3" fill="#00FFA3"/>
    
    <!-- Left Candlestick Wing -->
    <line x1="-24" y1="10" x2="-24" y2="55" stroke="#00D2FF" stroke-width="1.5"/>
    <rect x="-30" y="18" width="12" height="25" rx="2" fill="#00D2FF"/>
    
    <!-- Right Candlestick Wing -->
    <line x1="24" y1="10" x2="24" y2="55" stroke="#00D2FF" stroke-width="1.5"/>
    <rect x="18" y="18" width="12" height="25" rx="2" fill="#00D2FF"/>
  </g>

  <!-- Greek Alpha Signature under Chest -->
  <path d="M 235,360 C 220,360 210,345 220,335 C 230,325 245,340 255,355 C 262,365 270,370 280,370" 
        fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/>

  <!-- Typography -->
  <text x="250" y="440" text-anchor="middle" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="20" letter-spacing="4">RECURSIVE ALPHA</text>
  <text x="250" y="460" text-anchor="middle" fill="#00B8D9" font-family="monospace" font-weight="600" font-size="10" letter-spacing="2">// MICROSTRUCTURE RADAR</text>
</svg>'''

# 4. Candidate 4: The Nautilus Spiral (Fibonacci Alpha Cephalopod)
c4_nautilus = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#040D1A"/>
      <stop offset="100%" stop-color="#0B2038"/>
    </linearGradient>
    <linearGradient id="spiral-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="40%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>
    <filter id="glow4" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <rect width="500" height="500" rx="90" fill="url(#bg4)"/>

  <!-- Concentric Fibonacci Rings -->
  <circle cx="230" cy="235" r="180" fill="none" stroke="#1E3A5F" stroke-width="1.5" stroke-dasharray="3,6"/>
  <circle cx="230" cy="235" r="110" fill="none" stroke="#1E3A5F" stroke-width="1" stroke-dasharray="2,4" opacity="0.6"/>

  <!-- Geometric Nautilus Shell: Mathematical Partition Chambers (Recursive Hedge Architecture) -->
  <g stroke="#0E2A47" stroke-width="2">
    <!-- Chamber Sectors radiating from the pole -->
    <path d="M 230,235 L 370,170" stroke="#1E3A5F"/>
    <path d="M 230,235 L 340,90" stroke="#1E3A5F"/>
    <path d="M 230,235 L 230,65" stroke="#1E3A5F"/>
    <path d="M 230,235 L 120,95" stroke="#1E3A5F"/>
    <path d="M 230,235 L 80,180" stroke="#1E3A5F"/>
    <path d="M 230,235 L 90,290" stroke="#1E3A5F"/>
    <path d="M 230,235 L 160,360" stroke="#1E3A5F"/>
    <path d="M 230,235 L 270,375" stroke="#1E3A5F"/>
    <path d="M 230,235 L 360,330" stroke="#1E3A5F"/>
  </g>

  <!-- The Golden Recursive Spiral flowing directly into Greek Alpha -->
  <g filter="url(#glow4)">
    <!-- Main Shell Outer Arc & Alpha Extension -->
    <path d="M 230,235 
             A 20,20 0 0,1 250,220 
             A 35,35 0 0,1 275,255 
             A 60,60 0 0,1 220,295 
             A 100,100 0 0,1 130,210 
             A 150,150 0 0,1 250,85 
             C 330,85 390,140 400,220 
             C 410,290 365,340 310,340 
             C 255,340 220,295 180,240 
             C 145,190 100,190 70,225 
             C 40,260 55,305 90,325" 
          fill="none" stroke="url(#spiral-grad)" stroke-width="12" stroke-linecap="round"/>
  </g>

  <!-- Quant Data Nodes along the Spiral Path -->
  <g fill="#10B981">
    <circle cx="275" cy="255" r="4"/>
    <circle cx="220" cy="295" r="5"/>
    <circle cx="130" cy="210" r="6"/>
    <circle cx="250" cy="85" r="7"/>
    <circle cx="400" cy="220" r="6" fill="#F59E0B"/>
    <circle cx="310" cy="340" r="5" fill="#06B6D4"/>
  </g>

  <!-- Cephalopod Eye at center core -->
  <circle cx="230" cy="235" r="9" fill="#040D1A" stroke="#10B981" stroke-width="2.5"/>
  <circle cx="230" cy="235" r="3" fill="#FFFFFF"/>

  <!-- Mathematical Golden Formula Annotation -->
  <text x="230" y="160" text-anchor="middle" fill="#10B981" font-family="monospace" font-size="11" opacity="0.7">r = a · e^(bθ)</text>

  <!-- Typography -->
  <text x="250" y="420" text-anchor="middle" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="22" letter-spacing="4">RECURSIVE ALPHA</text>
  <text x="250" y="442" text-anchor="middle" fill="#10B981" font-family="monospace" font-weight="600" font-size="11" letter-spacing="2">// LOGARITHMIC HEDGE</text>
</svg>'''

with open("assets/logos/candidate_1_ouroboros_viper.svg", "w") as f:
    f.write(c1_ouroboros)

with open("assets/logos/candidate_2_corvid_disassembler.svg", "w") as f:
    f.write(c2_corvid)

with open("assets/logos/candidate_3_radar_owl.svg", "w") as f:
    f.write(c3_owl)

with open("assets/logos/candidate_4_nautilus_spiral.svg", "w") as f:
    f.write(c4_nautilus)

print("Generated all 4 SVG candidates successfully!")
