# MTD
"A dynamic Moving Target Defence (MTD) framework that autonomously hops application ports every 30 seconds with zero-downtime, deploying active honeypots on vacated ports to trap and auto-block attackers."
# 🛡️ Moving Target Defence (MTD) System with Active Deception

## 📌 Project Overview
This project implements a **Moving Target Defence (MTD)** architecture designed to proactively defend web applications by continuously shifting their attack surface. By changing the application's hosting port every 30 seconds, it renders attacker reconnaissance useless. 

This repository contains the **Phase 1 (40% Proof of Concept)** core engine, which includes zero-downtime port hopping and an active deception mechanism (Honeypot) to trap and block malicious actors.

## 🚀 Core Features (PoC Phase)
* **Autonomous Port Hopping:** Uses TOTP (Time-based One-Time Password) algorithms to seamlessly shift the application to a new port every 30 seconds.
* **Zero-Downtime Smart Proxy:** A reverse proxy gateway that holds and routes legitimate user traffic during port transitions without dropping connections.
* **Active Deception (Honeypots):** Automatically deploys a decoy application on the recently vacated port.
* **Automated Retaliation:** Captures the IP addresses of attackers who hit the honeypot and instantly blocks them using system firewall rules (`iptables`).
* **Real-Time Dashboard:** A live visual interface built with Streamlit to monitor the active secure port and view trapped attacker IPs.
* **Hacker Simulation Engine:** An automated script to simulate an attacker's delayed reconnaissance, proving the efficiency of the honeypot trap.

## 🛠️ Tech Stack
* **Language:** Python 3
* **Containerization:** Docker & Docker SDK for Python
* **Web Framework:** Flask (App & Proxy), Streamlit (Live Dashboard)
* **Security & Automation:** `pyotp` (Time-sync logic), `iptables` (Auto-blocking)

## 📂 Project Structure
* `orchestrator.py` - The core daemon managing Docker containers and firewall blocks.
* `smart_proxy.py` - The seamless reverse proxy gateway.
* `dashboard.py` - Streamlit UI for live monitoring. 
* `hacker_sim.py` - Script to simulate a cyber attack on the vacated port.
* `/real_app/` - Dockerized legitimate web application.
* `/honeypot/` - Dockerized deception trap with fake IIS headers.
