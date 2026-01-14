import tkinter as tk
from tkinter import ttk
import random

class Hasta:
    def __init__(self, pid, tedavi_suresi, aciliyet, renk):
        self.pid = pid  
        self.toplam_tedavi_suresi = tedavi_suresi
        self.kalan_sure = tedavi_suresi
        self.aciliyet = aciliyet  
        self.durum = "BEKLEMEDE"
        self.ana_renk = renk 
        self.renk = renk
        
        self.muayene_suresi_kullanilan = 0    
        self.dinamik_kota = 3    
        
        self.tahlil_ihtimali = random.randint(5, 20) 
        self.tahlil_suresi = 0 
        
        self.kaynak_cakismasi = False   
        self.ani_komplikasyon = False  
        self.yanlis_teshis = False      
        self.malzeme_yetersiz = False   
        
        self.res_admin = 50
        self.res_gecmis = random.randint(20, 50)
        self.res_tahlil_veri = random.randint(10, 30)
        self.res_ilac = random.randint(30, 100)
        self.res_monitor = random.randint(30, 80)
        
        self.toplam_kaynak_ihtiyaci = self.res_admin + self.res_gecmis + \
                                      self.res_tahlil_veri + self.res_ilac + self.res_monitor
        
        self.numa_node = 0 

class HastaneSim:
    def __init__(self, root):
        self.root = root
        self.root.title("ACİL SERVİS YÖNETİM SİSTEMİ (Hastane Simülasyonu)")
        self.root.geometry("1650x950")

        self.hastalar = []
        self.bekleme_salonu = []   
        self.laboratuvar = []       
        self.taburcu_listesi = []   
        
        self.doktor_sayisi = 4
        self.odalar = [None] * self.doktor_sayisi 
        self.secili_oda_index = 0
        
        self.protokol_no = 1000 
        self.calisiyor = False
        self.simulasyon_hizi = 1000 
        self.baz_muayene_suresi = 3 
        self.zamanlayici_id = None 
        self.kaos_aktif = False 
        
        self.TOPLAM_HASTANE_STOK = 4096 
        self.merkezi_stok_kullanim = 0
        self.bolgesel_stok_boyutu = self.TOPLAM_HASTANE_STOK // 4
        self.bolgesel_stok_kullanim = [0] * 4 

        self.gui_kurulum()

    def gui_kurulum(self):

        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.sol_cerceve = tk.Frame(self.main_pane)
        self.main_pane.add(self.sol_cerceve, width=1200)

        self.sag_cerceve = tk.Frame(self.main_pane, bg="#ecf0f1", relief=tk.SUNKEN, bd=2)
        self.main_pane.add(self.sag_cerceve)

        ayarlar_frame = tk.Frame(self.sol_cerceve, pady=5, bg="#2c3e50")
        ayarlar_frame.pack(fill=tk.X)

        tk.Label(ayarlar_frame, text="YÖNETİM PANELİ", bg="#2c3e50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        
        self.arch_var = tk.StringVar(value="Merkezi Stok (SMP)")
        arch_menu = ttk.Combobox(ayarlar_frame, textvariable=self.arch_var, values=["Merkezi Stok (SMP)", "Bölgesel Stok (NUMA)"], state="readonly", width=20)
        arch_menu.pack(side=tk.LEFT, padx=5)
        arch_menu.bind("<<ComboboxSelected>>", self.mimari_degistir)

        self.core_var = tk.StringVar(value="4 Doktor")
        core_menu = ttk.Combobox(ayarlar_frame, textvariable=self.core_var, values=["1 Doktor", "2 Doktor", "3 Doktor", "4 Doktor"], state="readonly", width=10)
        core_menu.pack(side=tk.LEFT, padx=5)
        core_menu.bind("<<ComboboxSelected>>", self.doktor_sayisi_degistir)

        self.algo_var = tk.StringVar(value="Round Robin + Aciliyet")
        algo_menu = ttk.Combobox(ayarlar_frame, textvariable=self.algo_var, values=["Sıralı Muayene (RR)", "Round Robin + Aciliyet", "Geliş Sırası (FCFS)", "Kısa İşlem Önceliği (SJF)", "Sadece Aciliyet (Priority)"], state="readonly", width=25)
        algo_menu.pack(side=tk.LEFT, padx=5)
        algo_menu.bind("<<ComboboxSelected>>", lambda e: self.zorla_sirala())

        tk.Label(ayarlar_frame, text="Akış Hızı:", bg="#2c3e50", fg="white").pack(side=tk.LEFT)
        self.hiz_slider = tk.Scale(ayarlar_frame, from_=100, to=2000, orient=tk.HORIZONTAL, command=self.hiz_ayarla, bg="#2c3e50", fg="white", length=80)
        self.hiz_slider.set(1000)
        self.hiz_slider.pack(side=tk.LEFT)
        
        self.ram_label = tk.Label(ayarlar_frame, text=f"STOK: 0 / {self.TOPLAM_HASTANE_STOK} Birim", bg="#2c3e50", fg="#f1c40f", font=("Arial", 10, "bold"))
        self.ram_label.pack(side=tk.RIGHT, padx=20)

        action_frame = tk.Frame(self.sol_cerceve, pady=10, bg="#bdc3c7", relief=tk.RAISED)
        action_frame.pack(fill=tk.X)

        tk.Button(action_frame, text="Hasta Girişi (+)", command=self.hasta_ekle, bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        self.baslat_btn = tk.Button(action_frame, text="MESAİYİ BAŞLAT ▶", command=self.simulasyon_toggle, bg="#2980b9", fg="white", font=("Arial", 10, "bold"))
        self.baslat_btn.pack(side=tk.LEFT, padx=10)
        
        self.kaos_var = tk.StringVar(value="Acil Durum Seç...")
        kaos_secenekleri = ["Acil Durum Seç...", "⚠️ Ekipman Çakışması", "🔒 Kaynak Kilitlenmesi", "⚖️ Hasta Yığılması", "💥 Ani Komplikasyon", "🚫 Yanlış Dosya/Teshis", "💾 Malzeme Tükendi"]
        kaos_menu = ttk.Combobox(action_frame, textvariable=self.kaos_var, values=kaos_secenekleri, state="readonly", width=22)
        kaos_menu.pack(side=tk.LEFT, padx=10)
        tk.Button(action_frame, text="Oluştur ⚡", command=self.kaos_tetikle, bg="#c0392b", fg="white").pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.sol_cerceve, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.canvas_tiklama)
        self.temizle_btn = tk.Button(self.canvas, text="Arşivi Temizle 🗑️", command=lambda: setattr(self, 'taburcu_listesi', []), bg="#95a5a6", fg="white")

        log_frame = tk.LabelFrame(self.sol_cerceve, text="Hastane Günlüğü", height=80, bg="#f7f9f9")
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.log_text = tk.Text(log_frame, height=4, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, padx=5, pady=5)

        self.lbl_inspector = tk.Label(self.sag_cerceve, text=f"HASTA DOSYASI (ODA-{self.secili_oda_index})", bg="#ecf0f1", font=("Arial", 12, "bold"))
        self.lbl_inspector.pack(pady=(10, 0))
        
        self.mem_canvas = tk.Canvas(self.sag_cerceve, bg="white", width=320, height=650, relief=tk.RIDGE, bd=2)
        self.mem_canvas.pack(pady=5, padx=10)
        
        self.legend_frame = tk.Frame(self.sag_cerceve, bg="#ecf0f1")
        self.legend_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        tk.Label(self.legend_frame, text="Kaynak Kullanımı", font=("Arial", 10, "bold"), bg="#ecf0f1").pack(anchor="w")
        aciklamalar = [("KAYIT/ADMIN", "#8bc34a"), ("MONİTÖR/YAŞAM", "#81d4fa"), ("İLAÇ/SERUM", "#ffcc80"), ("TAHLİL VERİSİ", "#ef5350"), ("HASTA GEÇMİŞİ", "#ce93d8")]
        for isim, renk in aciklamalar:
            row = tk.Frame(self.legend_frame, bg="#ecf0f1")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, bg=renk, width=2, relief="solid", bd=1).pack(side=tk.LEFT, padx=(0, 5))
            tk.Label(row, text=isim, anchor="w", font=("Arial", 8, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)

        self.cizim_sabitleri()
        self.bos_dosya_ciz()
        self.kaynak_hesapla()

    def hiz_ayarla(self, val): self.simulasyon_hizi = int(val)
    def log(self, mesaj, tip="info"):
        renkler = {"info": "black", "error": "red", "warn": "#d35400", "success": "green", "io": "#f39c12"}
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"> {mesaj}\n", (tip))
        self.log_text.tag_config(tip, foreground=renkler.get(tip, "black"))
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    def rastgele_renk_getir(self): return random.choice(['#ef5350', '#ab47bc', '#5c6bc0', '#26c6da', '#8d6e63'])

    def kaynak_hesapla(self):
        aktif_hastalar = self.bekleme_salonu + self.laboratuvar + [p for p in self.odalar if p]
        self.merkezi_stok_kullanim = 0
        self.bolgesel_stok_kullanim = [0] * 4
        is_numa = "Bölgesel" in self.arch_var.get()
        for p in aktif_hastalar:
            if is_numa:
                if p.numa_node >= self.doktor_sayisi: p.numa_node = p.numa_node % self.doktor_sayisi
                self.bolgesel_stok_kullanim[p.numa_node] += p.toplam_kaynak_ihtiyaci
            else:
                self.merkezi_stok_kullanim += p.toplam_kaynak_ihtiyaci
        self.stok_label_guncelle()

    def stok_label_guncelle(self):
        if "Merkezi" in self.arch_var.get():
            yuzde = (self.merkezi_stok_kullanim / self.TOPLAM_HASTANE_STOK) * 100
            self.ram_label.config(text=f"MERKEZİ DEPO: {self.merkezi_stok_kullanim} / {self.TOPLAM_HASTANE_STOK} ({yuzde:.1f}%)", fg="#f1c40f")
        else:
            total = sum(self.bolgesel_stok_kullanim)
            self.ram_label.config(text=f"BÖLGESEL TOPLAM: {total} / {self.TOPLAM_HASTANE_STOK}", fg="#3498db")

    def doktor_sayisi_degistir(self, event=None):
        yeni_sayi = int(self.core_var.get().split()[0])
        self.log(f"Doktor Sayısı: {yeni_sayi} olarak ayarlandı.", "warn")
        if yeni_sayi == 1: self.arch_var.set("Merkezi Stok (SMP)")
        for p in self.odalar:
            if p: self.bekleme_salonu.insert(0, p)
        self.doktor_sayisi = yeni_sayi
        self.odalar = [None] * yeni_sayi
        self.secili_oda_index = 0
        self.bolgesel_stok_boyutu = self.TOPLAM_HASTANE_STOK // yeni_sayi
        self.kaynak_hesapla()
        self.canvas_guncelle()

    def mimari_degistir(self, event=None):
        mod = self.arch_var.get()
        if self.doktor_sayisi == 1 and "Bölgesel" in mod:
            self.arch_var.set("Merkezi Stok (SMP)")
            return
        self.log(f"Depo Modeli: {mod}", "warn")
        if "Bölgesel" in mod:
            aktif_hastalar = self.bekleme_salonu + self.laboratuvar + [p for p in self.odalar if p]
            for p in aktif_hastalar: p.numa_node = random.randint(0, self.doktor_sayisi - 1)
        self.kaynak_hesapla()
        self.canvas_guncelle()

    def hasta_ekle(self):
        tedavi_sure = random.randint(5, 15)
        aciliyet = random.randint(1, 10) 
        h = Hasta(self.protokol_no, tedavi_sure, aciliyet, self.rastgele_renk_getir())
        
        if "Merkezi" in self.arch_var.get():
            if self.merkezi_stok_kullanim + h.toplam_kaynak_ihtiyaci > self.TOPLAM_HASTANE_STOK:
                self.log(f"HATA: Hastane Kapasitesi Dolu! (Stok Yetersiz)", "error")
                return
        else:
            baslangic_depo = random.randint(0, self.doktor_sayisi - 1)
            atandi = False
            for i in range(self.doktor_sayisi):
                node = (baslangic_depo + i) % self.doktor_sayisi
                if self.bolgesel_stok_kullanim[node] + h.toplam_kaynak_ihtiyaci <= self.bolgesel_stok_boyutu:
                    h.numa_node = node
                    atandi = True
                    break
            if not atandi:
                self.log(f"HATA: Tüm Bölgesel Depolar Dolu!", "error")
                return

        bonus = 5 if h.aciliyet <= 3 else 0 
        h.dinamik_kota = self.baz_muayene_suresi + bonus
        
        self.hastalar.append(h)
        self.bekleme_salonu.append(h)
        self.protokol_no += 1
        
        self.sirayi_duzenle()
        self.kaynak_hesapla() 
        self.canvas_guncelle()

    def sirayi_duzenle(self):
        algo = self.algo_var.get()
        if "Geliş Sırası" in algo: # FCFS
            self.bekleme_salonu.sort(key=lambda x: x.pid)
        elif "Kısa İşlem" in algo: # SJF
            self.bekleme_salonu.sort(key=lambda x: x.kalan_sure)
        elif "Aciliyet" in algo: # Priority ve RR+Priority
            self.bekleme_salonu.sort(key=lambda x: x.aciliyet)
    
    def zorla_sirala(self):
        self.sirayi_duzenle()
        self.canvas_guncelle()

    def simulasyon_toggle(self):
        if self.kaos_aktif: return 
        self.calisiyor = not self.calisiyor
        if self.calisiyor:
            self.baslat_btn.config(text="MOLA VER ⏸", bg="#e74c3c")
            self.dongu_calistir()
        else:
            self.baslat_btn.config(text="DEVAM ET ▶", bg="#2980b9")
            if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)

    def dongu_calistir(self):
        if not self.calisiyor or self.kaos_aktif: return
        algo = self.algo_var.get()
        is_numa = "Bölgesel" in self.arch_var.get()
        
        for i in range(len(self.laboratuvar) - 1, -1, -1):
            h = self.laboratuvar[i]
            h.tahlil_suresi -= 1
            if h.tahlil_suresi <= 0:
                h.durum = "BEKLEMEDE"
                h.renk = h.ana_renk
                self.bekleme_salonu.append(h)
                self.laboratuvar.pop(i)
                self.sirayi_duzenle() 
                self.log(f"Hasta {h.pid}: Tahlil sonuçları çıktı, sıraya döndü.", "success")
        
        for i in range(self.doktor_sayisi):
            h = self.odalar[i]
            if h and not h.kaynak_cakismasi:
                if random.randint(1, 100) <= h.tahlil_ihtimali and h.kalan_sure > 1:
                    h.durum = "TAHLILDE"
                    h.renk = "#f1c40f"
                    h.tahlil_suresi = random.randint(3, 8)
                    h.muayene_suresi_kullanilan = 0
                    self.laboratuvar.append(h)
                    self.odalar[i] = None
                    self.log(f"Oda-{i}: Hasta {h.pid} röntgene/tahlile gönderildi.", "io")
                    continue

                h.kalan_sure -= 1
                h.muayene_suresi_kullanilan += 1
                
                if h.kalan_sure <= 0:
                    h.durum = "TABURCU"
                    self.taburcu_listesi.append(h)
                    self.odalar[i] = None
                    self.kaynak_hesapla() 
                    self.log(f"Hasta {h.pid} tedavisi tamamlandı ve taburcu oldu.", "success")
                elif "Round Robin" in algo: 
                    limit = h.dinamik_kota if "+ Aciliyet" in algo else self.baz_muayene_suresi
                    if h.muayene_suresi_kullanilan >= limit:
                        h.durum = "BEKLEMEDE"
                        h.muayene_suresi_kullanilan = 0
                        self.bekleme_salonu.append(h)
                        self.odalar[i] = None
                        if "+ Aciliyet" in algo: self.sirayi_duzenle()

        ignore_numa = ("SJF" in algo) or ("Priority" in algo) or ("Aciliyet" in algo)

        for i in range(self.doktor_sayisi):
            if self.odalar[i] is None and self.bekleme_salonu:
                secilen_hasta = None
                
                if ignore_numa:
                    secilen_hasta = self.bekleme_salonu[0]
                
                elif is_numa:
                    for p in self.bekleme_salonu:
                        if p.numa_node == i:
                            secilen_hasta = p
                            break
                    if not secilen_hasta: secilen_hasta = self.bekleme_salonu[0]
                
                else:
                    secilen_hasta = self.bekleme_salonu[0]
                
                if secilen_hasta:
                    self.bekleme_salonu.remove(secilen_hasta)
                    secilen_hasta.durum = "MUAYENEDE"
                    self.odalar[i] = secilen_hasta

        self.canvas_guncelle()
        self.zamanlayici_id = self.root.after(self.simulasyon_hizi, self.dongu_calistir)

    def canvas_tiklama(self, event):
        for i, coords in enumerate(self.oda_kutulari):
            x1, y1, x2, y2 = coords
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.secili_oda_index = i
                self.lbl_inspector.config(text=f"HASTA DOSYASI (ODA-{i})")
                self.canvas_guncelle()
                return

    def kaos_tetikle(self):
        senaryo = self.kaos_var.get()
        if "Çakışması" in senaryo and self.bekleme_salonu and self.doktor_sayisi > 1:
            self.kaos_aktif = True
            if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)
            self.canvas_guncelle()
            self.root.after(3000, self.kaos_coz)
        elif "Kilitlenmesi" in senaryo: 
            aktif = [p for p in self.odalar if p]
            if len(aktif) >= 2:
                self.kaos_aktif = True
                if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)
                aktif[0].kaynak_cakismasi = True; aktif[1].kaynak_cakismasi = True
                self.canvas_guncelle()
                self.root.after(3000, lambda: self.kilitlenme_coz(aktif[0], aktif[1]))
            else: self.log("Kaynak kilitlenmesi için en az 2 aktif hasta lazım.", "error")
        elif "Yığılması" in senaryo: 
            for _ in range(6):
                h = Hasta(self.protokol_no, 30, 1, "#8e44ad") 
                self.hastalar.append(h)
                self.bekleme_salonu.insert(0, h)
                self.protokol_no += 1
            self.sirayi_duzenle()
            self.kaynak_hesapla()
            self.canvas_guncelle()
            self.log("Zincirleme trafik kazası! Çok sayıda acil hasta geldi.", "warn")
        elif "Komplikasyon" in senaryo and self.odalar[self.secili_oda_index]:
            target = self.odalar[self.secili_oda_index]
            target.ani_komplikasyon = True
            self.kaos_aktif = True
            if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)
            self.canvas_guncelle()
            self.root.after(3000, self.kaos_coz)
        elif "Yanlış" in senaryo and self.odalar[self.secili_oda_index]: 
            target = self.odalar[self.secili_oda_index]
            target.yanlis_teshis = True
            self.kaos_aktif = True
            if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)
            self.canvas_guncelle()
            self.root.after(3000, self.kaos_coz)
        elif "Tükendi" in senaryo and self.odalar[self.secili_oda_index]: 
            target = self.odalar[self.secili_oda_index]
            target.malzeme_yetersiz = True
            self.kaos_aktif = True
            if self.zamanlayici_id: self.root.after_cancel(self.zamanlayici_id)
            self.canvas_guncelle()
            self.root.after(3000, self.kaos_coz)

    def kaos_coz(self):
        self.kaos_aktif = False
        for p in self.hastalar:
            p.ani_komplikasyon = False; p.yanlis_teshis = False; p.malzeme_yetersiz = False
        self.log("Acil durum kontrol altına alındı.", "success")
        if self.calisiyor: self.dongu_calistir()

    def kilitlenme_coz(self, p1, p2):
        self.kaos_aktif = False
        p1.kaynak_cakismasi = False; p2.kaynak_cakismasi = False
        p2.durum = "SEVK EDİLDİ"
        if p2 in self.odalar: self.odalar[self.odalar.index(p2)] = None
        self.taburcu_listesi.append(p2)
        self.kaynak_hesapla()
        self.log("Kaynak çatışması çözüldü (Hasta sevk edildi).", "success")
        if self.calisiyor: self.dongu_calistir()

    def bos_dosya_ciz(self):
        self.mem_canvas.delete("all")
        self.mem_canvas.create_text(160, 325, text="Oda Boş / Dosya Yok", font=("Arial", 14), fill="gray")

    def cizim_sabitleri(self):
        self.canvas.delete("all")
        w = 1200
        
        self.bekleme_alani = (50, 50, w-50, 180)
        self.lab_alani = (50, 200, w-50, 330)
        self.taburcu_alani = (50, 600, w-50, 700)

        self.canvas.create_rectangle(self.bekleme_alani, outline="#7f8c8d", dash=(5,5))
        self.canvas.create_text(60, 40, text="BEKLEME SALONU (Triyaj Sırası)", anchor="w", font=("Arial", 10, "bold"), fill="#7f8c8d")
        
        self.canvas.create_rectangle(self.lab_alani, outline="#f1c40f", dash=(5,5), width=2)
        self.canvas.create_text(60, 190, text="TAHLİL / RÖNTGEN BEKLEYENLER", anchor="w", font=("Arial", 10, "bold"), fill="#f39c12")

        oda_y = 380
        kutu_w = 140
        bosluk = 40
        bas_x = (w - (self.doktor_sayisi * kutu_w + (self.doktor_sayisi - 1) * bosluk)) / 2
        
        self.oda_kutulari = []
        is_numa = "Bölgesel" in self.arch_var.get()
        
        for i in range(self.doktor_sayisi):
            x = bas_x + i * (kutu_w + bosluk)
            col = "blue" if i == self.secili_oda_index else "#e74c3c"
            kalinlik = 4 if i == self.secili_oda_index else 2

            self.canvas.create_rectangle(x, oda_y, x+kutu_w, oda_y+130, outline=col, width=kalinlik)
            
            hasta = self.odalar[i]
            etiket = f"ODA-{i}"
            text_col = col
            if is_numa and hasta and hasta.numa_node != i:
                etiket += " (DIŞ DEPO!)"
                text_col = "magenta"
                stok_hedef_x = bas_x + hasta.numa_node * (kutu_w + bosluk) + kutu_w/2
                stok_hedef_y = oda_y + 145
                self.canvas.create_line(x+kutu_w/2, oda_y+130, stok_hedef_x, stok_hedef_y, dash=(4,4), fill="magenta", width=2, arrow=tk.LAST)

            self.canvas.create_text(x+5, oda_y-15, text=etiket, anchor="w", font=("Arial", 9, "bold"), fill=text_col)
            self.oda_kutulari.append((x, oda_y, x+kutu_w, oda_y+130))

            if is_numa:
                depo_y = oda_y + 140
                self.canvas.create_rectangle(x, depo_y, x+kutu_w, depo_y+20, outline="gray")
                yuzde = self.bolgesel_stok_kullanim[i] / self.bolgesel_stok_boyutu
                gorsel_yuzde = min(yuzde, 1.0)
                doluluk_w = kutu_w * gorsel_yuzde
                doluluk_col = "#3498db" if yuzde < 0.8 else "#e74c3c"
                self.canvas.create_rectangle(x, depo_y, x+doluluk_w, depo_y+20, fill=doluluk_col, outline="")
                txt = f"{self.bolgesel_stok_kullanim[i]}/{self.bolgesel_stok_boyutu}"
                self.canvas.create_text(x+kutu_w/2, depo_y+10, text=txt, font=("Arial", 7), fill="black")

        self.canvas.create_rectangle(self.taburcu_alani, outline="#7f8c8d", dash=(5,5))
        self.canvas.create_text(60, 590, text="TABURCU EDİLENLER / SEVKLER", anchor="w", font=("Arial", 10, "bold"), fill="#7f8c8d")
        self.canvas.create_window(w-100, 590, window=self.temizle_btn)

    def hasta_ciz(self, x, y, h, aktif=False):
        w, boy = 120, 70
        bg = "#34495e" if h.kaynak_cakismasi else h.renk
        cerceve = "red" if aktif else "black"
        if h.durum == "TAHLILDE": cerceve = "#f1c40f"; kalinlik=3
        else: kalinlik = 2

        self.canvas.create_rectangle(x, y, x+w, y+boy, fill=bg, outline=cerceve, width=kalinlik)
        self.canvas.create_text(x+5, y+15, text=f"P.NO: {h.pid}", anchor="w", font=("Arial", 10, "bold"), fill="white" if h.kaynak_cakismasi else "black")
        self.canvas.create_text(x+w-5, y+15, text=f"Acil: {h.aciliyet}", anchor="e", font=("Arial", 9, "bold"), fill="black")
        
        pct = max(0, h.kalan_sure / h.toplam_tedavi_suresi)
        self.canvas.create_rectangle(x+5, y+35, x+5+(w-10), y+45, fill="white", outline="")
        self.canvas.create_rectangle(x+5, y+35, x+5+(w-10)*pct, y+45, fill="#2c3e50", outline="")
        
        durum_metni = "KİLİTLENDİ" if h.kaynak_cakismasi else (f"Test ({h.tahlil_suresi}dk)" if h.durum == "TAHLILDE" else f"Kalan: {h.kalan_sure}dk")
        self.canvas.create_text(x+w/2, y+60, text=durum_metni, font=("Arial", 9, "bold" if h.durum=="TAHLILDE" else "normal"))

    def dosya_detay_ciz(self, hasta):
        c = self.mem_canvas
        c.delete("all")
        w, h = 320, 650
        
        if not hasta:
            c.create_text(w/2, h/2, text="ODA BOŞ", font=("Arial", 16), fill="gray")
            return

        c.create_rectangle(0, 0, w, 50, fill=hasta.renk, outline="")
        node_txt = f" (Depo {hasta.numa_node})" if "Bölgesel" in self.arch_var.get() else ""
        c.create_text(w/2, 25, text=f"PROTOKOL: {hasta.pid}{node_txt}", font=("Arial", 12, "bold"), fill="black")

        available_h = h - 60 
        total_virtual_kb = hasta.res_admin + hasta.res_monitor + hasta.res_ilac + hasta.res_tahlil_veri + hasta.res_gecmis + 100
        min_h = 40 
        
        def calc_h(val): return max(min_h, (val / total_virtual_kb) * available_h)

        kernel_h = calc_h(hasta.res_admin)
        curr_y = 60
        
        if hasta.yanlis_teshis:
            c.create_rectangle(10, curr_y, w-10, curr_y+kernel_h, fill="red", outline="black", width=2)
            c.create_text(w/2, curr_y+kernel_h/2, text="YANLIŞ DOSYA / TESHİS!", font=("Arial", 12, "bold"), fill="white")
            return

        c.create_rectangle(10, curr_y, w-10, curr_y+kernel_h, fill="#8bc34a", outline="black")
        c.create_text(w/2, curr_y+kernel_h/2, text="KAYIT & SİGORTA", font=("Arial", 9, "bold"))
        curr_y += kernel_h + 5

        stack_kb = hasta.res_monitor
        if hasta.ani_komplikasyon: stack_kb += 200
        stack_h = calc_h(stack_kb)
        col = "#e74c3c" if hasta.ani_komplikasyon else "#81d4fa"
        
        c.create_rectangle(10, curr_y, w-10, curr_y+stack_h, fill=col, outline="black")
        c.create_text(w/2, curr_y+20, text="ANLIK YAŞAM BULGULARI", font=("Arial", 10, "bold"))
        
        if hasta.ani_komplikasyon:
            c.create_text(w/2, curr_y+stack_h/2, text="ANİ KOMPLİKASYON!", font=("Arial", 14, "bold"), fill="white")
            return
        curr_y += stack_h 

        void_h = calc_h(80)
        c.create_line(20, curr_y, 20, curr_y+void_h, dash=(4,4), fill="gray")
        c.create_line(w-20, curr_y, w-20, curr_y+void_h, dash=(4,4), fill="gray")
        curr_y += void_h

        heap_h = calc_h(hasta.res_ilac)
        c.create_rectangle(10, curr_y, w-10, curr_y+heap_h, fill="#ffcc80", outline="black")
        c.create_text(w/2, curr_y+heap_h/2, text="İLAÇ & SERUM STOK", font=("Arial", 10, "bold"))
        curr_y += heap_h + 5

        if hasta.malzeme_yetersiz:
             c.create_rectangle(10, 60, w-10, h-10, fill="red", stipple="gray50")
             c.create_text(w/2, h/2, text="STOK TÜKENDİ!", font=("Arial", 20), fill="white")
             return
        
        data_h = calc_h(hasta.res_tahlil_veri)
        c.create_rectangle(10, curr_y, w-10, curr_y+data_h, fill="#ef5350", outline="black")
        c.create_text(w/2, curr_y+data_h/2, text="TAHLİL SONUÇLARI", font=("Arial", 9, "bold"))
        curr_y += data_h + 5
        
        text_h = calc_h(hasta.res_gecmis)
        c.create_rectangle(10, curr_y, w-10, curr_y+text_h, fill="#ce93d8", outline="black")
        c.create_text(w/2, curr_y+text_h/2, text="TIBBİ GEÇMİŞ", font=("Arial", 9, "bold"))

    def canvas_guncelle(self):
        self.canvas.delete("all")
        self.cizim_sabitleri()
        
        sx, sy = self.bekleme_alani[0] + 10, self.bekleme_alani[1] + 20
        for i, h in enumerate(self.bekleme_salonu):
            if i < 7: self.hasta_ciz(sx + i*135, sy, h)

        wx, wy = self.lab_alani[0] + 10, self.lab_alani[1] + 20
        for i, h in enumerate(self.laboratuvar):
            if i < 7: self.hasta_ciz(wx + i*135, wy, h)
            
        for i, h in enumerate(self.odalar):
            if h:
                kutu = self.oda_kutulari[i]
                cx, cy = kutu[0], kutu[1]
                self.hasta_ciz(cx+10, cy+30, h, aktif=True)

        sx, sy = self.taburcu_alani[0] + 10, self.taburcu_alani[1] + 20
        for i, h in enumerate(self.taburcu_listesi):
            if i < 7:
                orj_renk = h.renk; h.renk = "#bdc3c7"
                self.hasta_ciz(sx + i*135, sy, h)
                h.renk = orj_renk
        
        hedef = self.odalar[self.secili_oda_index] if self.secili_oda_index < self.doktor_sayisi else None
        self.dosya_detay_ciz(hedef)
        
        if self.kaos_aktif and "Çakışması" in self.kaos_var.get():
             cx, cy = self.canvas.winfo_width()/2, 300 
             
             self.canvas.create_rectangle(cx-60, cy-30, cx+60, cy+30, fill="#34495e", outline="white", width=2)
             self.canvas.create_text(cx, cy, text="DEFİBRİLATÖR\n(Ortak Cihaz)", font=("Arial", 10, "bold"), fill="white", justify=tk.CENTER)
             
             if self.doktor_sayisi >= 2 and len(self.oda_kutulari) >= 2:
                 c0_rect = self.oda_kutulari[0]
                 c1_rect = self.oda_kutulari[1]
                 c0_x = (c0_rect[0] + c0_rect[2]) / 2 
                 c0_y = c0_rect[1] 
                 c1_x = (c1_rect[0] + c1_rect[2]) / 2 
                 c1_y = c1_rect[1]
                 
                 self.canvas.create_line(c0_x, c0_y, cx-30, cy+30, fill="red", width=4, arrow=tk.LAST, dash=(5,2))
                 self.canvas.create_line(c1_x, c1_y, cx+30, cy+30, fill="red", width=4, arrow=tk.LAST, dash=(5,2))
                 
             self.canvas.create_text(cx, cy-50, text="⚠️ CİHAZ KAVGASI!", font=("Arial", 16, "bold"), fill="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = HastaneSim(root)
    root.mainloop()