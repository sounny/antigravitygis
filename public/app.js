/* ==========================================================================
   AntigravityGIS by Sounny - Frontend Interactivity & Mouse-Following Canvas
   Created by Sounny (sounny.com)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Code Tabs in Code Inspector Box
  const tabBtns = document.querySelectorAll('.tab-btn');
  const codeContent = document.getElementById('code-content');

  const snippets = {
    arcgis: `<span class="code-comment"># ArcGIS Pro AI Copilot Execution in Geoprocessing Pane</span>
<span class="code-keyword">import</span> arcpy
<span class="code-keyword">from</span> agent_core <span class="code-keyword">import</span> GISAntigravityAgent

<span class="code-comment"># Initialize AntigravityGIS Agent on your active Google Antigravity account</span>
agent = <span class="code-func">GISAntigravityAgent</span>()

<span class="code-comment"># User Prompt in ArcGIS Pro</span>
prompt = <span class="code-str">"Inspect feature classes in target.gdb and buffer streams by 50 meters."</span>
response = <span class="code-keyword">await</span> agent.<span class="code-func">execute_prompt</span>(prompt)
arcpy.<span class="code-func">AddMessage</span>(response)`,

    installer: `<span class="code-comment"># PowerShell 1-Click Multi-Platform Installer</span>
<span class="code-keyword">Write-Host</span> <span class="code-str">"Installing AntigravityGIS Copilot..."</span> -ForegroundColor Cyan

<span class="code-comment"># Option A: Run PowerShell Installer (Bypasses execution policy)</span>
powershell -ExecutionPolicy Bypass -File .\Install-AntigravityGIS.ps1

<span class="code-comment"># Option B: Double-click Install-AntigravityGIS.bat</span>`,

    pyqgis: `<span class="code-comment"># Native QGIS PyQGIS Dock Panel AI Copilot</span>
<span class="code-keyword">from</span> qgis.core <span class="code-keyword">import</span> QgsProject, Qgis
<span class="code-keyword">from</span> agent_core <span class="code-keyword">import</span> GISAntigravityAgent

<span class="code-comment"># Initialize AI Copilot with QGIS Project inspection tools</span>
agent = <span class="code-func">GISAntigravityAgent</span>()

<span class="code-comment"># Execute natural-language PyQGIS analysis</span>
prompt = <span class="code-str">"Audit CRS projections of all active layers and report missing spatial indexes."</span>
result = <span class="code-keyword">await</span> agent.<span class="code-func">execute_prompt</span>(prompt)
<span class="code-func">print</span>(result)`
  };

  if (tabBtns.length > 0 && codeContent) {
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const target = btn.getAttribute('data-tab');
        if (snippets[target]) {
          codeContent.innerHTML = snippets[target];
        }
      });
    });
  }

  // ==========================================================================
  // Google Antigravity Interactive Mouse-Following Canvas Animation
  // ==========================================================================
  const canvas = document.getElementById('hero-canvas');
  const heroSection = document.querySelector('.hero');

  if (canvas && heroSection) {
    const ctx = canvas.getContext('2d');
    let width = (canvas.width = heroSection.offsetWidth);
    let height = (canvas.height = heroSection.offsetHeight);

    let mouse = {
      x: width / 2,
      y: height / 2,
      targetX: width / 2,
      targetY: height / 2,
      radius: 180
    };

    window.addEventListener('resize', () => {
      width = canvas.width = heroSection.offsetWidth;
      height = canvas.height = heroSection.offsetHeight;
    });

    heroSection.addEventListener('mousemove', (e) => {
      const rect = heroSection.getBoundingClientRect();
      mouse.targetX = e.clientX - rect.left;
      mouse.targetY = e.clientY - rect.top;
    });

    heroSection.addEventListener('mouseleave', () => {
      mouse.targetX = width / 2;
      mouse.targetY = height / 2;
    });

    // Particle nodes for spatial grid
    const numParticles = 45;
    const particles = [];

    for (let i = 0; i < numParticles; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        radius: Math.random() * 2.5 + 1.5,
        color: Math.random() > 0.3 ? '#0079c1' : '#059669'
      });
    }

    function animate() {
      ctx.clearRect(0, 0, width, height);

      // Smooth mouse position lerp
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;

      // Update and draw spatial node particles & connecting lines
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Distance to mouse cursor
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < mouse.radius) {
          const force = (mouse.radius - dist) / mouse.radius;
          p.x -= (dx / dist) * force * 1.5;
          p.y -= (dy / dist) * force * 1.5;
        }

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();

        // Connect nearby particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const pdx = p.x - p2.x;
          const pdy = p.y - p2.y;
          const pDist = Math.sqrt(pdx * pdx + pdy * pdy);

          if (pDist < 110) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 121, 193, ${0.15 * (1 - pDist / 110)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      requestAnimationFrame(animate);
    }

    animate();
  }
});
