"""
HP Semiconductor Analyzer Wiring Guide Dialog.

Opens from Help > Wiring Guide… (F1).  A scrollable QTextBrowser window
describing how to connect the HP 4145A/B, 4155A/B/C, 4156A/B/C, and 4280A
for every measurement type the app supports.

Rendered as a styled HTML page — no extra dependencies beyond Qt Widgets.
"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextBrowser, QSizePolicy,
)
from PyQt5.QtCore import Qt, QUrl

# ── Colour scheme (dark theme) ───────────────────────────────────────────────

_BG        = "#0F0F1A"
_BG_PANEL  = "#1A1A2E"
_BG_WIDGET = "#252540"
_TEXT_PRI  = "#E8E8FF"
_TEXT_SEC  = "#A0A0C0"
_TEXT_MUT  = "#666688"
_AMBER     = "#FFB300"
_AMBER_LT  = "#FFCC44"
_INFO      = "#42A5F5"
_BORDER    = "#2E2E50"
_BORDER_LT = "#3A3A60"
_GREEN     = "#4CAF50"

_CSS = f"""
<style>
  body  {{ background:{_BG}; color:{_TEXT_PRI};
           font-family:'Segoe UI',Arial,sans-serif; font-size:10pt;
           margin:16px 24px; }}
  h1    {{ color:{_AMBER}; font-size:15pt;
           border-bottom:1px solid {_BORDER}; padding-bottom:6px; margin-top:4px; }}
  h2    {{ color:{_AMBER_LT}; font-size:12pt; margin-top:22px;
           margin-bottom:4px; border-left:3px solid {_AMBER};
           padding-left:8px; }}
  h3    {{ color:{_TEXT_PRI}; font-size:10pt; margin-top:14px;
           margin-bottom:3px; font-weight:600; }}
  p     {{ color:{_TEXT_SEC}; margin:4px 0 10px 0; line-height:1.5; }}
  a     {{ color:{_INFO}; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  code  {{ background:{_BG_WIDGET}; color:{_AMBER_LT};
           padding:1px 5px; border-radius:3px; font-family:Consolas,monospace; }}
  .toc  {{ background:{_BG_PANEL}; border:1px solid {_BORDER};
           border-radius:6px; padding:10px 16px; margin-bottom:18px; }}
  .toc p {{ margin:2px 0; color:{_TEXT_SEC}; font-size:9pt; }}
  table {{ border-collapse:collapse; width:100%; margin:10px 0 16px 0;
           font-size:9.5pt; }}
  th    {{ background:{_BG_WIDGET}; color:{_AMBER};
           padding:6px 10px; text-align:left;
           border:1px solid {_BORDER_LT}; }}
  td    {{ padding:5px 10px; border:1px solid {_BORDER};
           color:{_TEXT_SEC}; vertical-align:top; }}
  tr:nth-child(even) td {{ background:{_BG_PANEL}; }}
  pre   {{ background:#080810; color:#A8D8A8;
           border:1px solid {_BORDER}; border-radius:4px;
           padding:12px 14px; font-family:Consolas,monospace;
           font-size:9pt; line-height:1.4; overflow-x:auto; }}
  .note {{ background:{_BG_PANEL}; border-left:3px solid {_INFO};
           padding:8px 12px; margin:10px 0; border-radius:0 4px 4px 0; }}
  .warn {{ background:{_BG_PANEL}; border-left:3px solid {_AMBER};
           padding:8px 12px; margin:10px 0; border-radius:0 4px 4px 0; }}
  .note p, .warn p {{ color:{_TEXT_SEC}; margin:2px 0; }}
  hr    {{ border:none; border-top:1px solid {_BORDER}; margin:20px 0; }}
</style>
"""

_HTML = _CSS + """
<h1>HP Semiconductor Analyzer — Wiring Guide</h1>

<div class="toc">
  <p><b>Contents</b></p>
  <p><a href="#gpib">GPIB Connection (Keysight 82351B &amp; NI GPIB-USB)</a></p>
  <p><a href="#models">Instrument Channel Map</a></p>
  <p><a href="#mosfet">MOSFET Transfer / Output Curves</a></p>
  <p><a href="#diode">Diode I-V</a></p>
  <p><a href="#resistor">Resistor I-V</a></p>
  <p><a href="#cv">C-V Measurement (HP 4280A)</a></p>
  <p><a href="#vdp">Van der Pauw Sheet Resistance</a></p>
  <p><a href="#kelvin">Kelvin 4-Probe Resistance</a></p>
  <p><a href="#hall">Hall Bar Measurement</a></p>
  <p><a href="#generic">Generic 4-Port</a></p>
  <p><a href="#safety">Safety Notes</a></p>
</div>

<!-- ──────────────────────────────────────────────────────── -->
<a name="gpib"></a>
<h2>GPIB Connection</h2>

<h3>Keysight 82351B (PCIe/PCI GPIB card)</h3>
<p>Install <b>Keysight IO Libraries Suite</b> before connecting the card.
The driver registers a VISA resource manager automatically.
PyVISA will detect it as the default backend.</p>
<ol>
  <li>Install Keysight IO Libraries Suite (download from keysight.com).</li>
  <li>Install the 82351B card in a PCIe ×1 (or PCI) slot.</li>
  <li>Connect the GPIB cable from the card to the instrument's rear-panel GPIB connector.</li>
  <li>Power on the instrument.</li>
  <li>In the app, click <b>Scan VISA</b> — the instrument will appear as
      <code>GPIB0::&lt;addr&gt;::INSTR</code>.</li>
</ol>
<div class="note"><p>Default GPIB addresses: HP 4145A/B → <b>17</b>,
HP 4155/4156 → <b>17</b>, HP 4280A → <b>22</b>.
Verify / change on the instrument front panel under System → GPIB.</p></div>

<h3>NI GPIB-USB-HS (USB to GPIB adapter)</h3>
<p>Install <b>NI-VISA</b> and the <b>NI-488.2</b> driver before plugging in the adapter.
Windows will prompt for a driver — point it to the NI installation.</p>
<ol>
  <li>Install NI-VISA and NI-488.2 (ni.com/downloads).</li>
  <li>Plug the GPIB-USB adapter into a USB port.</li>
  <li>Connect the GPIB cable to the instrument.</li>
  <li>Power on the instrument, then click <b>Scan VISA</b> in the app.</li>
</ol>
<div class="note"><p>If the instrument does not appear after scanning, use
<b>NI MAX</b> (Measurement &amp; Automation Explorer) to verify the adapter is
detected and the GPIB address matches the instrument setting.</p></div>

<!-- ──────────────────────────────────────────────────────── -->
<a name="models"></a>
<h2>Instrument Channel Map</h2>

<table>
  <tr>
    <th>Instrument</th><th>SMUs</th><th>VSUs</th><th>VMUs</th><th>Notes</th>
  </tr>
  <tr>
    <td>HP 4145A / 4145B</td>
    <td>SMU1–SMU4 (ch 1–4)</td>
    <td>VSU1–VSU2 (ch 5–6)</td>
    <td>VMU1–VMU2 (ch 7–8)</td>
    <td>4145A: pre-IEEE 488.2, no *IDN?<br>4145B: adds *IDN? and quasi-static C-V</td>
  </tr>
  <tr>
    <td>HP 4155A / 4155B / 4155C</td>
    <td>SMU1–SMU2 only</td>
    <td>VSU1–VSU2</td>
    <td>—</td>
    <td>2-SMU variant of the 4156 family</td>
  </tr>
  <tr>
    <td>HP 4156A / 4156B / 4156C</td>
    <td>SMU1–SMU4</td>
    <td>VSU1–VSU2</td>
    <td>VMU1–VMU2</td>
    <td>4156C is the current production model</td>
  </tr>
  <tr>
    <td>HP 4280A</td>
    <td>Single C-V terminal</td>
    <td>—</td>
    <td>—</td>
    <td>1 MHz C-V plotter; use C-V tab only</td>
  </tr>
</table>

<p>Channel numbering in the software follows the instrument's own convention:
<code>CH1</code>=SMU1, <code>CH2</code>=SMU2, …  Assign roles (Gate, Drain, Source)
in each measurement panel's <b>Channel Assignment</b> section.</p>

<!-- ──────────────────────────────────────────────────────── -->
<a name="mosfet"></a>
<h2>MOSFET Transfer / Output Curves</h2>
<p>Standard 3-terminal FET characterization in a probe station or socket.</p>

<table>
  <tr><th>Device terminal</th><th>Instrument channel</th><th>Notes</th></tr>
  <tr><td>Gate (G)</td>   <td>SMU1 (Force HI)</td> <td>Voltage sweep / step source</td></tr>
  <tr><td>Drain (D)</td>  <td>SMU2 (Force HI)</td> <td>Drain bias / sweep source</td></tr>
  <tr><td>Source (S)</td> <td>SMU3 or ground</td>   <td>Typically 0 V; use ground clip if only 2 SMUs</td></tr>
  <tr><td>Body (B)</td>   <td>SMU4 or ground</td>   <td>Optional; ground for enhancement-mode</td></tr>
</table>

<pre>
  ┌──────────────────────────────────────────────────────────────────┐
  │   HP 4145/4155/4156                                              │
  │                                                                  │
  │   SMU1 ──[Force]──────────────────── Gate                       │
  │   SMU2 ──[Force]──────────────────── Drain                      │
  │   SMU3 ──[Force/GND]──────────────── Source                     │
  │   SMU4 ──[Force/GND]──────────────── Body (optional)            │
  └──────────────────────────────────────────────────────────────────┘
</pre>

<div class="warn"><p>Use triax cables and guarded probe tips when measuring
below 100 pA to avoid leakage current from cable capacitance.</p></div>

<!-- ──────────────────────────────────────────────────────── -->
<a name="diode"></a>
<h2>Diode I-V</h2>

<table>
  <tr><th>Terminal</th><th>Channel</th><th>Notes</th></tr>
  <tr><td>Anode (+)</td>   <td>SMU1 (Force HI)</td> <td>Voltage sweep source</td></tr>
  <tr><td>Cathode (−)</td> <td>SMU2 or GND</td>      <td>Ground reference</td></tr>
</table>

<p>For reverse-bias breakdown, increase the SMU compliance current and reduce
the voltage step size near the expected breakdown voltage.</p>

<!-- ──────────────────────────────────────────────────────── -->
<a name="resistor"></a>
<h2>Resistor I-V</h2>

<p>Two-terminal or four-terminal (Kelvin) resistance measurement.</p>

<table>
  <tr><th>2-wire (standard)</th><th>4-wire (Kelvin)</th></tr>
  <tr>
    <td>
      SMU1 Force HI → terminal 1<br>
      SMU1 Force LO → terminal 2<br>
      (or terminal 2 to chassis GND)
    </td>
    <td>
      SMU1 Force HI → terminal 1<br>
      SMU2 Force LO → terminal 2<br>
      VMU1 Sense  → terminal 1<br>
      VMU2 Sense  → terminal 2<br>
      (4156/4145 only; eliminates lead resistance)
    </td>
  </tr>
</table>

<!-- ──────────────────────────────────────────────────────── -->
<a name="cv"></a>
<h2>C-V Measurement (HP 4280A)</h2>

<p>The HP 4280A has a single coaxial BIAS output and a MEAS HI/LO pair for
the 1 MHz AC test signal.  Connect as follows:</p>

<pre>
  ┌──────────────────────────────────────────────────────────────────┐
  │   HP 4280A                                                       │
  │                                                                  │
  │   BIAS OUTPUT ───────────────────────── Gate / top electrode    │
  │   MEAS HI    ────────────────────────── Gate / top electrode    │
  │   MEAS LO    ────────────────────────── Substrate / bottom      │
  │   GND shield ────────────────────────── Chuck / substrate GND   │
  └──────────────────────────────────────────────────────────────────┘
</pre>

<div class="note"><p>Use a shielded triax-to-coax adapter at the DUT.
Keep cable lengths ≤ 1 m and perform an OPEN/SHORT compensation before
measuring.  The 4280A compensation sequence is in the C-V tab.</p></div>

<!-- ──────────────────────────────────────────────────────── -->
<a name="vdp"></a>
<h2>Van der Pauw Sheet Resistance</h2>

<p>Four-terminal contact layout.  Label contacts A, B, C, D clockwise.</p>

<pre>
         A ───── B
         │       │
         D ───── C
</pre>

<table>
  <tr><th>Measurement step</th><th>Current through</th><th>Voltage across</th></tr>
  <tr><td>R_AB,CD</td><td>A → B (SMU1)</td><td>C–D (VMU1 or SMU3/4 in volt-meter mode)</td></tr>
  <tr><td>R_BC,DA</td><td>B → C (SMU1)</td><td>D–A</td></tr>
  <tr><td>R_CD,AB</td><td>C → D (SMU1)</td><td>A–B</td></tr>
  <tr><td>R_DA,BC</td><td>D → A (SMU1)</td><td>B–C</td></tr>
</table>

<p>The software sequences these automatically.  Assign
<b>I+</b>=SMU1 (current source), <b>V+</b>=SMU2 or VMU1 (voltage sense).</p>

<!-- ──────────────────────────────────────────────────────── -->
<a name="kelvin"></a>
<h2>Kelvin 4-Probe Resistance</h2>

<table>
  <tr><th>Probe</th><th>Channel</th><th>Role</th></tr>
  <tr><td>I+</td><td>SMU1 Force HI</td><td>Current source +</td></tr>
  <tr><td>I−</td><td>SMU1 Force LO or GND</td><td>Current source −</td></tr>
  <tr><td>V+</td><td>VMU1 or SMU3 (sense only)</td><td>Voltage sense +</td></tr>
  <tr><td>V−</td><td>VMU2 or SMU4 (sense only)</td><td>Voltage sense −</td></tr>
</table>

<div class="note"><p>Space the voltage probes between the current probes
on the sample.  The current probe contact resistance is excluded from the
measured voltage because negligible current flows through the voltage probes.</p></div>

<!-- ──────────────────────────────────────────────────────── -->
<a name="hall"></a>
<h2>Hall Bar Measurement</h2>

<p>Six-terminal Hall bar geometry.  The long axis carries current;
transverse contacts sense the Hall voltage.</p>

<pre>
  I+  ─────┬──────────── Hall bar ──────────┬─────  I−
           │                                │
           ●VH+                           VH−●
           │                                │
           ●VL+                           VL−●
</pre>

<table>
  <tr><th>Contact</th><th>Channel</th></tr>
  <tr><td>I+</td><td>SMU1 (current source +)</td></tr>
  <tr><td>I−</td><td>SMU2 or GND (current return)</td></tr>
  <tr><td>VH+</td><td>VMU1 or SMU3 (Hall voltage +)</td></tr>
  <tr><td>VH−</td><td>VMU2 or SMU4 (Hall voltage −)</td></tr>
</table>

<!-- ──────────────────────────────────────────────────────── -->
<a name="generic"></a>
<h2>Generic 4-Port</h2>

<p>All four SMU channels available for arbitrary assignment.
Useful for custom 2-, 3-, or 4-terminal measurements not covered
by the dedicated panels.  Configure each channel's role (V sweep,
I sweep, constant V, constant I, or floating) in the panel.</p>

<!-- ──────────────────────────────────────────────────────── -->
<a name="safety"></a>
<h2>Safety Notes</h2>

<div class="warn">
  <p><b>Maximum output limits — verify before applying bias</b></p>
  <p>HP 4145A/B: SMU ±100 V / 100 mA.  VSU ±20 V (voltage only, no current measurement).</p>
  <p>HP 4155/4156: SMU ±100 V / 100 mA (4156C: ±200 V with HVSMU option).
     VSU ±20 V.</p>
  <p>HP 4280A: BIAS ±100 V DC; AC test signal 30 mVrms at 1 MHz.</p>
</div>

<ul>
  <li>Always set a <b>compliance current</b> appropriate for your device
      (typically 10 mA for MOSFETs, 100 mA for power devices).</li>
  <li>Keep the instrument in <b>standby</b> while changing device connections
      — use the Measurement Execute / standby sequence on the front panel,
      or rely on the software's built-in abort before each new measurement.</li>
  <li>Use properly guarded triax cables for low-current (sub-nA) measurements
      to avoid ground loops and cable leakage.</li>
  <li>The GPIB cable must be ≤ 20 m total length (sum of all segments).
      Use only IEEE 488 certified cables; ordinary data cables cause errors.</li>
</ul>
"""


class WiringGuideDialog(QDialog):
    """Non-modal HTML wiring guide dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HP Semiconductor Analyzer — Wiring Guide")
        self.resize(820, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        browser = QTextBrowser()
        browser.setOpenLinks(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(_HTML)
        browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 0, 8, 0)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


try:
    from PyQt5.QtWidgets import QSizePolicy
except ImportError:
    pass
