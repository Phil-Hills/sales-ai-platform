import './style.css'

const startBtn = document.querySelector('#start-thinking');
const terminal = document.querySelector('#terminal-output');

const swarmSteps = [
    { node: "SWARM", msg: "Initializing Agentic Swarm v5.2.0...", color: "#64ffda" },
    { node: "SENTINEL", msg: "Monitoring pipeline integrity. Security status: GREEN.", color: "#4c9aff" },
    { node: "RESEARCH", msg: "Querying Salesforce MORE platform for Lead #8821...", color: "#e6f1ff" },
    { node: "RESEARCH", msg: "Data recovered. Type: Refinance, LTV: 75%, DNC: CLEAN.", color: "#e6f1ff" },
    { node: "JASON", msg: "Formulating empathetic outreach strategy...", color: "#004fb6" },
    { node: "JASON", msg: "Planning pass: Acknowledge LTV, suggest 'Smarter Way to Work'.", color: "#004fb6" },
    { node: "SENTINEL", msg: "COMPLIANCE CHECK: Logic grounded in NMLS Duty Gate.", color: "#4c9aff" },
    { node: "SWARM", msg: "Generating Thought Signature [BLAKE3]...", color: "#64ffda" },
    { node: "CRYPTO", msg: "tsig_7f2b9a1c8d3e4f5a - VERIFIED.", color: "#8892b0" },
    { node: "SWARM", msg: "Jason Agent: READY FOR OUTBOUND.", color: "#64ffda" }
];

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function typeWriter(text, element, speed = 20) {
    for (let i = 0; i < text.length; i++) {
        element.innerHTML += text.charAt(i);
        await sleep(speed);
    }
    element.innerHTML += '<br>';
}

startBtn.addEventListener('click', async () => {
    if (startBtn.disabled) return;
    startBtn.disabled = true;
    startBtn.innerText = "SWARM THINKING...";

    terminal.innerHTML = "";

    for (const step of swarmSteps) {
        const nodeSpan = document.createElement('span');
        nodeSpan.style.color = step.color;
        nodeSpan.style.fontWeight = "bold";
        nodeSpan.innerText = `> [${step.node}] `;

        terminal.appendChild(nodeSpan);
        await typeWriter(step.msg, terminal);
        terminal.scrollTop = terminal.scrollHeight;
        await sleep(200);
    }

    startBtn.innerText = "SIMULATION COMPLETE";
    await sleep(2000);
    startBtn.innerText = "SIMULATE THINKING PASS";
    startBtn.disabled = false;
});
