import math
import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector

def get_conn():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="phdpython22!",
        database="brake_analysis"
    )

def save_simulation_to_db(material, params, summary):
    try:
        conn = get_conn()
        cursor = conn.cursor()

        sql = """
        INSERT INTO simulations
        (material, rho, k, alpha, surface_peak, back_peak, avg_final, peak_stress)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        vals = (
            material,
            params["rho"],
            params["k"],
            params["alpha"],
            summary["surface_peak"],
            summary["back_peak"],
            summary["avg_final"],
            summary["peak_stress"]
        )

        cursor.execute(sql, vals)
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Failed to save simulation:", e)


def braking_energy(M, v):
    return 0.5 * M * v**2

def disc_area_from_diameter(D_outer, inner_frac=0.5):
    Ro = D_outer / 2
    Ri = inner_frac * Ro
    return math.pi * (Ro**2 - Ri**2), Ro, Ri

def simple_temperature_model(q_in, k, rho, cp, t_brake, T_amb):
    alpha = k / (rho * cp)

    T_surface = q_in / math.sqrt(math.pi * k * rho * cp * t_brake)
    T_back = T_surface / 3
    T_avg = (T_surface + T_back) / 2
    return T_amb + T_surface, T_amb + T_back, T_amb + T_avg

def calculate_thermal_stress(T, T_ref, alpha, E, nu=0.3):
    return E * alpha * (T - T_ref) / (1 - nu)

#TKINTER Part
class App:
    def __init__(self, root):
        self.root = root
        root.title("Brake Disc Thermal Analysis — Steel 15CDv6")
        root.geometry("1000x600")
        title = tk.Label(root, text="Brake Disc Thermal Analysis — Steel 15CDv6",
                         bg="#003366",
                         fg="white",
                         font=("Arial", 18, "bold"),
                         pady=10)
        title.pack(fill="x")
        # END ADD
        self.build_ui()

    def build_ui(self):
        frm = ttk.LabelFrame(self.root, text="Material properties & mechanical conditions ", padding=10)
        frm.pack(side="left", fill="y", padx=10, pady=10)

        self.entries = {}
        params = [
            ("Mass (kg)", "10000"),
            ("Speed (m/s)", "40"),
            ("Braking time (s)", "5"),
            ("Young's modulus (GPa)", "210"),            
            ("Heat capacity c (J/kgK)", "460"),
            ("Diameter (m)", "1.0"),
            ("Convection coeff h (W/m2K)", "100"),
            ("Ambient T (°C)", "24"),
            ("Density ρ (kg/m3)", "7800"),
            ("Conductivity k (W/mK)", "35"),
            ("Expansion α (1/K)", "1.3e-5"),
            ("Friction coefficient μ", "0.4"),
        ]

        for lbl, val in params:
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=lbl, width=22).pack(side="left")
            ent = ttk.Entry(row, width=12)
            ent.insert(0, val)
            ent.pack(side="right")
            self.entries[lbl] = ent

        ttk.Button(frm, text="Run Simulation", command=self.run_simulation).pack(pady=10)

        # RESULTS
        res = ttk.LabelFrame(self.root, text="Simulation Results", padding=10)
        res.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.results_text = tk.Text(res, width=60, height=30)
        self.results_text.pack(fill="both", expand=True)


    def run_simulation(self):
        try:
            # INPUTS
            M = float(self.entries["Mass (kg)"].get())
            v = float(self.entries["Speed (m/s)"].get())
            t_brake = float(self.entries["Braking time (s)"].get())
            E = float(self.entries["Young's modulus (GPa)"].get()) * 1e9
            c = float(self.entries["Heat capacity c (J/kgK)"].get())
            D = float(self.entries["Diameter (m)"].get())
            h = float(self.entries["Convection coeff h (W/m2K)"].get())
            T_amb = float(self.entries["Ambient T (°C)"].get())
            rho = float(self.entries["Density ρ (kg/m3)"].get())
            k = float(self.entries["Conductivity k (W/mK)"].get())
            alpha = float(self.entries["Expansion α (1/K)"].get())
            mu = float(self.entries["Friction coefficient μ"].get())

            
            A_contact, Ro, Ri = disc_area_from_diameter(D)

            Ek = braking_energy(M, v)
            Q_disc = Ek / 2
            q0 = Q_disc / (A_contact * t_brake)

            surface_peak, back_peak, avg_final = simple_temperature_model(
                q0, k, rho, c, t_brake, T_amb
            )

            peak_stress = calculate_thermal_stress(surface_peak, T_amb, alpha, E) / 1e6

            params_dict = {"rho": rho, "k": k, "alpha": alpha}
            summary = {
                "surface_peak": surface_peak,
                "back_peak": back_peak,
                "avg_final": avg_final,
                "peak_stress": peak_stress
            }

            save_simulation_to_db("Steel 15CDv6", params_dict, summary)
            txt = f"""
=== SIMULATION RESULTS ===

ρ: {rho}
k: {k}
α: {alpha}
μ: {mu}

Peak surface T: {surface_peak:.2f} °C
Peak back-face T: {back_peak:.2f} °C
Final average T: {avg_final:.2f} °C

Peak thermal stress: {peak_stress:.2f} MPa

(Simulation saved to MySQL)
"""
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", txt)

        except Exception as e:
            messagebox.showerror("Error", f"Input error:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()