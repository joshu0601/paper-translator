"""Built-in demo paper.

A short, self-contained (fictional) paper is rendered to a real PDF with
PyMuPDF and pushed through the normal pipeline, so the demo exercises text
extraction, structure detection, translation and RAG end to end without
requiring the user to find a PDF first.
"""

from __future__ import annotations

import pymupdf

TITLE = "Deep Reinforcement Learning for Joint Computation Offloading and Resource Allocation in Mobile Edge Computing"
AUTHORS = "Wei-Lun Chen, Mei-Ling Huang, and Jonathan R. Park"
AFFILIATION = "Department of Computer Science, National Example University, Taipei, Taiwan"

# (heading, [paragraphs]) — headings use numbering so the parser can detect them.
SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Abstract",
        [
            "Mobile Edge Computing (MEC) brings computation and storage resources close to mobile users, enabling latency-sensitive applications such as augmented reality and autonomous driving. However, deciding which tasks to offload and how much bandwidth and computing capacity to allocate is a challenging problem under time-varying channels and stochastic task arrivals. In this paper we formulate the joint computation offloading and resource allocation problem as a Markov Decision Process (MDP) and propose DRL-JORA, a Deep Reinforcement Learning (DRL) framework based on Proximal Policy Optimization (PPO). Simulation results show that DRL-JORA reduces the average task latency by 27.4% and energy consumption by 19.8% compared with the best baseline, while maintaining a task completion ratio above 96%.",
        ],
    ),
    (
        "1 Introduction",
        [
            "The explosive growth of mobile applications has created an unprecedented demand for low-latency, computation-intensive services. Cloud computing alleviates the limited capability of mobile devices, but the long propagation distance between users and remote data centers introduces significant delay [1]. Mobile Edge Computing (MEC) addresses this limitation by deploying servers at the network edge, for example at base stations, so that tasks can be processed within a few milliseconds of the user [2].",
            "Despite these advantages, edge servers have far less capacity than the cloud, and wireless channels fluctuate rapidly. A mobile device therefore has to decide whether to execute a task locally, offload it to an edge server, or forward it to the cloud, while the operator has to allocate limited bandwidth and CPU cycles among competing users. Existing heuristics and convex optimization methods [3], [4] require accurate models of the environment and often re-solve the problem at every time slot, which is impractical in highly dynamic settings.",
            "In this paper, we propose DRL-JORA, a model-free framework that learns an offloading and resource allocation policy directly from interaction with the environment. The main contributions of this paper are summarized as follows. First, we formulate the joint problem as a Markov Decision Process whose reward balances latency and energy consumption. Second, we design a PPO-based agent with an action-masking mechanism that guarantees feasible allocations. Third, extensive simulations demonstrate that DRL-JORA outperforms four representative baselines across a wide range of system loads.",
        ],
    ),
    (
        "2 Related Work",
        [
            "Computation offloading in MEC has been studied extensively. Early works such as [3] adopt Lyapunov optimization to obtain asymptotically optimal decisions, while [4] applies game theory to model the competition among users. These approaches rely on explicit system models and become intractable as the number of users grows.",
            "More recently, deep reinforcement learning has been applied to offloading problems. Deep Q-Network (DQN) based schemes [5] discretize the action space and therefore struggle with continuous resource allocation. Deep Deterministic Policy Gradient (DDPG) methods [6] support continuous actions but are known to be sensitive to hyper-parameters. Multi-Agent Reinforcement Learning (MARL) has also been explored [7]; however, communication overhead between agents limits its scalability. Different from these works, DRL-JORA uses a single PPO agent with action masking, which combines a discrete offloading decision with continuous resource allocation in one policy network.",
        ],
    ),
    (
        "3 System Model and Problem Formulation",
        [
            "We consider an MEC system consisting of one base station equipped with an edge server and a set of $N$ mobile users, denoted by $\\mathcal{N} = \\{1, 2, \\dots, N\\}$. Time is divided into slots of equal length $\\tau$. At the beginning of slot $t$, user $n$ generates a computation task characterized by the tuple $(D_n(t), C_n(t), T_n^{max})$, where $D_n(t)$ is the input data size in bits, $C_n(t)$ is the required number of CPU cycles, and $T_n^{max}$ is the maximum tolerable latency.",
            "Local execution. If the task is processed locally, the latency and energy consumption are given by $T_n^{loc}(t) = C_n(t) / f_n^{loc}$ and $E_n^{loc}(t) = \\kappa (f_n^{loc})^2 C_n(t)$, where $f_n^{loc}$ is the CPU frequency of the device and $\\kappa$ is the effective switched capacitance.",
            "Edge execution. If the task is offloaded, the uplink transmission rate follows the Shannon capacity $r_n(t) = b_n(t) \\log_2 \\left(1 + \\frac{p_n h_n(t)}{N_0 b_n(t)}\\right)$, where $b_n(t)$ is the allocated bandwidth, $p_n$ is the transmit power, $h_n(t)$ is the channel gain and $N_0$ is the noise power spectral density. The total offloading latency is $T_n^{off}(t) = D_n(t)/r_n(t) + C_n(t)/f_n^{edge}(t)$, where $f_n^{edge}(t)$ is the edge CPU frequency allocated to user $n$.",
            "Problem formulation. Let $a_n(t) \\in \\{0, 1\\}$ denote the offloading decision. The objective is to minimize the long-term weighted sum of latency and energy consumption over all users subject to bandwidth, computing and deadline constraints:",
            "$$\\min_{a, b, f} \\lim_{T \\to \\infty} \\frac{1}{T} \\sum_{t=1}^{T} \\sum_{n=1}^{N} \\left[ \\alpha T_n(t) + \\beta E_n(t) \\right] \\quad (1)$$",
            "subject to $\\sum_n b_n(t) \\le B$, $\\sum_n f_n^{edge}(t) \\le F$ and $T_n(t) \\le T_n^{max}$ for all $n$ and $t$, where $\\alpha$ and $\\beta$ are weighting factors. Problem (1) is a mixed-integer non-linear program and is NP-hard in general, which motivates our learning-based solution.",
        ],
    ),
    (
        "4 The DRL-JORA Framework",
        [
            "We reformulate problem (1) as a Markov Decision Process (MDP) defined by the tuple $(\\mathcal{S}, \\mathcal{A}, P, R, \\gamma)$. The agent resides at the base station and observes the global system state at every slot.",
            "State. The state $s_t$ consists of the task profiles $(D_n(t), C_n(t), T_n^{max})$ of all users, the channel gains $h_n(t)$, the remaining queue length at the edge server, and the residual battery level of each device. All quantities are normalized to $[0, 1]$.",
            "Action. The action $a_t = (a_n(t), b_n(t), f_n^{edge}(t))_{n \\in \\mathcal{N}}$ contains a binary offloading decision and two continuous allocation ratios for every user. Infeasible actions, for example allocating bandwidth to a user that executes locally, are removed by an action mask applied to the policy output.",
            "Reward. The reward function is defined as $R(s_t, a_t) = -\\sum_n \\left[ \\alpha T_n(t) + \\beta E_n(t) \\right] - \\lambda \\sum_n \\mathbb{1}\\{T_n(t) > T_n^{max}\\}$, where the last term penalizes deadline violations with a large constant $\\lambda$. Maximizing the cumulative discounted reward is therefore equivalent to minimizing the objective in (1) while respecting the deadline constraints.",
            "Learning algorithm. We adopt Proximal Policy Optimization (PPO) [8] because of its stability in high-dimensional hybrid action spaces. The actor network has two hidden layers of 256 neurons with ReLU activations and outputs a Bernoulli distribution for the offloading decision and a Beta distribution for each allocation ratio. The critic shares the first hidden layer. The clipped surrogate objective is $L^{CLIP}(\\theta) = \\mathbb{E}_t \\left[ \\min(\\rho_t(\\theta) \\hat{A}_t, \\text{clip}(\\rho_t(\\theta), 1-\\epsilon, 1+\\epsilon) \\hat{A}_t) \\right]$ with $\\epsilon = 0.2$.",
            "Fig. 1. Architecture of the DRL-JORA agent. The shared encoder processes the normalized state, and the masked actor produces discrete offloading decisions and continuous allocation ratios.",
        ],
    ),
    (
        "5 Performance Evaluation",
        [
            "Experimental setup. We simulate a single cell with a radius of 500 m and $N \\in \\{10, 20, 30, 40, 50\\}$ users. The system bandwidth is $B = 20$ MHz and the edge server provides $F = 40$ GHz of computing capacity. Task data sizes are uniformly distributed in $[0.5, 3]$ MB and required cycles in $[0.5, 2] \\times 10^9$. The channel follows the 3GPP urban macro model with Rayleigh fading. The weighting factors are $\\alpha = 0.6$ and $\\beta = 0.4$. Training uses a learning rate of $3 \\times 10^{-4}$, a discount factor of $\\gamma = 0.95$ and 2,000 episodes of 200 slots each. All results are averaged over 10 random seeds.",
            "Baselines. We compare DRL-JORA with four baselines: (i) Local-Only, where every task is executed on the device; (ii) Edge-Only, where every task is offloaded with equal resource sharing; (iii) Greedy, a heuristic that offloads the task with the largest local latency first; and (iv) DQN-Offload [5], a discrete deep reinforcement learning scheme. The evaluation metrics are the average task latency, the average energy consumption per task and the task completion ratio.",
            "Table 1. Average latency (ms), energy (mJ) and completion ratio (%) with N = 30 users.",
            "Results. Table 1 summarizes the results with 30 users. DRL-JORA achieves an average latency of 48.3 ms, which is 27.4% lower than DQN-Offload and 41.2% lower than Greedy. The average energy consumption of DRL-JORA is 19.8% lower than DQN-Offload, mainly because the continuous bandwidth allocation avoids the coarse discretization of DQN. The completion ratio remains above 96% for all system loads, whereas Local-Only drops below 70% when N = 50.",
            "Fig. 2. Average task latency versus the number of users. DRL-JORA maintains the lowest latency as the load increases.",
            "Ablation study. Removing the action mask increases the number of infeasible actions during early training and slows convergence by roughly 35%. Replacing the Beta distribution with a clipped Gaussian degrades the final latency by 6.1%, confirming that bounded action distributions are beneficial for allocation ratios.",
        ],
    ),
    (
        "6 Discussion and Limitations",
        [
            "Although DRL-JORA performs well in simulation, several limitations remain. First, the agent assumes perfect knowledge of the channel gains at the beginning of each slot; in practice channel estimation errors may degrade the policy. Second, the current design considers a single edge server, and extending it to multi-server cooperation would enlarge the action space considerably. Third, training requires about 2,000 episodes, which may be costly to obtain in a real deployment; transfer learning from simulation to reality is left for future work.",
        ],
    ),
    (
        "7 Conclusion",
        [
            "This paper studied joint computation offloading and resource allocation in Mobile Edge Computing. We formulated the problem as a Markov Decision Process and proposed DRL-JORA, a PPO-based framework with action masking that handles hybrid discrete-continuous actions. Simulation results demonstrated substantial latency and energy improvements over representative baselines. Future work includes multi-server cooperation, robustness to imperfect channel information and evaluation on a real testbed.",
        ],
    ),
    (
        "References",
        [
            "[1] M. Satyanarayanan, \"The emergence of edge computing,\" Computer, vol. 50, no. 1, pp. 30-39, 2017.",
            "[2] Y. Mao, C. You, J. Zhang, K. Huang, and K. B. Letaief, \"A survey on mobile edge computing: The communication perspective,\" IEEE Communications Surveys & Tutorials, vol. 19, no. 4, pp. 2322-2358, 2017.",
            "[3] Y. Mao, J. Zhang, and K. B. Letaief, \"Dynamic computation offloading for mobile-edge computing with energy harvesting devices,\" IEEE JSAC, vol. 34, no. 12, pp. 3590-3605, 2016.",
            "[4] X. Chen, L. Jiao, W. Li, and X. Fu, \"Efficient multi-user computation offloading for mobile-edge cloud computing,\" IEEE/ACM Trans. Netw., vol. 24, no. 5, pp. 2795-2808, 2016.",
            "[5] J. Li, H. Gao, T. Lv, and Y. Lu, \"Deep reinforcement learning based computation offloading and resource allocation for MEC,\" in Proc. IEEE WCNC, 2018.",
            "[6] Z. Chen and X. Wang, \"Decentralized computation offloading for multi-user mobile edge computing: A deep reinforcement learning approach,\" EURASIP J. Wireless Commun. Netw., 2020.",
            "[7] L. Huang, S. Bi, and Y.-J. A. Zhang, \"Deep reinforcement learning for online computation offloading in wireless powered mobile-edge computing networks,\" IEEE Trans. Mobile Comput., vol. 19, no. 11, pp. 2581-2593, 2020.",
            "[8] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, and O. Klimov, \"Proximal policy optimization algorithms,\" arXiv preprint arXiv:1707.06347, 2017.",
        ],
    ),
]

TABLE_ROWS = [
    ["Scheme", "Latency (ms)", "Energy (mJ)", "Completion (%)"],
    ["Local-Only", "112.6", "38.4", "81.2"],
    ["Edge-Only", "84.1", "21.7", "90.5"],
    ["Greedy", "82.1", "24.3", "92.8"],
    ["DQN-Offload", "66.5", "22.9", "94.1"],
    ["DRL-JORA (ours)", "48.3", "18.4", "96.7"],
]


def _draw_figure(page: pymupdf.Page, rect: pymupdf.Rect) -> None:
    """A simple block diagram so the demo has a real extractable image."""
    pix_doc = pymupdf.open()
    p = pix_doc.new_page(width=360, height=150)
    shape = p.new_shape()
    boxes = [("State s_t", 15), ("Shared encoder", 130), ("Masked actor", 245)]
    for label, x in boxes:
        r = pymupdf.Rect(x, 50, x + 100, 100)
        shape.draw_rect(r)
        shape.finish(color=(0.2, 0.2, 0.2), fill=(0.92, 0.94, 0.98), width=1.2)
        shape.insert_textbox(r, label, fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER, fontname="helv")
    for x in (115, 230):
        shape.draw_line(pymupdf.Point(x, 75), pymupdf.Point(x + 15, 75))
        shape.finish(color=(0.2, 0.2, 0.2), width=1.2)
    shape.commit()
    pix = p.get_pixmap(dpi=144)
    page.insert_image(rect, pixmap=pix)
    pix_doc.close()


def build_demo_pdf() -> bytes:
    """Render the demo paper as a single-column PDF."""
    doc = pymupdf.open()
    width, height = 595, 842
    margin = 56
    body_size = 10
    line_h = body_size * 1.45

    page = doc.new_page(width=width, height=height)
    y = margin

    def new_page() -> None:
        nonlocal page, y
        page = doc.new_page(width=width, height=height)
        y = margin

    def write(text: str, size: float, fontname: str, gap: float = 6.0) -> None:
        nonlocal y
        # Estimate height by laying the text out in a tall box first.
        box = pymupdf.Rect(margin, y, width - margin, height - margin)
        rc = page.insert_textbox(box, text, fontsize=size, fontname=fontname, lineheight=1.45)
        if rc < 0:  # did not fit: start a new page and retry
            new_page()
            box = pymupdf.Rect(margin, y, width - margin, height - margin)
            rc = page.insert_textbox(box, text, fontsize=size, fontname=fontname, lineheight=1.45)
        used = box.height - rc
        y += used + gap
        if y > height - margin - line_h * 2:
            new_page()

    write(TITLE, 16, "hebo", gap=10)
    write(AUTHORS, 11, "helv", gap=2)
    write(AFFILIATION, 9, "heit", gap=14)

    for heading, paragraphs in SECTIONS:
        write(heading, 12, "hebo", gap=6)
        for para in paragraphs:
            if para.startswith("Table 1."):
                # Draw a real table (extractable by find_tables) before its caption.
                rows = TABLE_ROWS
                col_w = (width - 2 * margin) / len(rows[0])
                row_h = 16
                if y + row_h * len(rows) + 40 > height - margin:
                    new_page()
                top = y
                for ri, row in enumerate(rows):
                    for ci, cell in enumerate(row):
                        r = pymupdf.Rect(margin + ci * col_w, top + ri * row_h, margin + (ci + 1) * col_w, top + (ri + 1) * row_h)
                        page.draw_rect(r, color=(0.3, 0.3, 0.3), width=0.6)
                        page.insert_textbox(r + (4, 3, 0, 0), cell, fontsize=8.5, fontname="hebo" if ri == 0 else "helv")
                y = top + row_h * len(rows) + 6
                write(para, 9, "heit", gap=10)
                continue
            if para.startswith("Fig. 1."):
                if y + 170 > height - margin:
                    new_page()
                _draw_figure(page, pymupdf.Rect(margin + 60, y, width - margin - 60, y + 150))
                y += 156
                write(para, 9, "heit", gap=10)
                continue
            if para.startswith("Fig. 2."):
                write(para, 9, "heit", gap=10)
                continue
            is_ref = heading == "References"
            write(para, body_size if not is_ref else 9, "helv", gap=8 if not is_ref else 4)

    for i, p in enumerate(doc, 1):
        p.insert_text(pymupdf.Point(width / 2 - 6, height - 30), str(i), fontsize=8, fontname="helv")

    out = doc.tobytes()
    doc.close()
    return out
