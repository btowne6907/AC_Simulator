import math

def get_p_sat(T_F):
    """ASHRAE-standard Tetens equation for vapor pressure (PSI)."""
    T_C = (T_F - 32.0) * 5.0 / 9.0
    P_sat_kPa = 0.61078 * math.exp((17.27 * T_C) / (T_C + 237.3))
    return P_sat_kPa * 0.145038

def get_dew_point(P_vapor_psi):
    """Inverse Tetens equation for perfect Dew Point resolution (°F)."""
    if P_vapor_psi <= 0:
        return 0.0
    Pv_kPa = P_vapor_psi / 0.145038
    alpha = math.log(Pv_kPa / 0.61078)
    DP_C = (237.3 * alpha) / (17.27 - alpha)
    return (DP_C * 9.0 / 5.0) + 32.0

def simulate_smart_family_ac(unit_selection, Tin, RHin_pct, Toutdoor, CFM=None):
    """
    Steady-state performance engine for Smart Family SACP-HS rental units.
    - Universally calibrated using the 10-Ton field test data.
    - Protected by an Enthalpy Governor and Tetens-grade Psychrometrics.
    """
    
    equipment_catalog = {
        "10-Ton Unit (SACP12A-HS)": {"Q_nominal": 120000, "default_cfm": 1600, "T_coil": 45.0},
        "20-Ton Unit (SACP20A-HS)": {"Q_nominal": 240000, "default_cfm": 3200, "T_coil": 45.0},
        "30-Ton Unit (SACP30A-HS)": {"Q_nominal": 360000, "default_cfm": 5000, "T_coil": 45.0},
        "40-Ton Unit (SACP40A-HS)": {"Q_nominal": 480000, "default_cfm": 6400, "T_coil": 45.0},
        "60-Ton Unit (SACP60A-HS)": {"Q_nominal": 720000, "default_cfm": 15000, "T_coil": 42.0},
        "80-Ton Unit (SACP80A-HS)": {"Q_nominal": 960000, "default_cfm": 12800, "T_coil": 42.0}
    }
    
    if unit_selection not in equipment_catalog:
        return None

    specs = equipment_catalog[unit_selection]
    Q_nominal = specs["Q_nominal"]
    T_coil = specs["T_coil"]
    if CFM is None: CFM = specs["default_cfm"]

    RHin = RHin_pct / 100.0
    Patm = 14.696  
    Cp = 0.240     
    hfg = 1061.0   

    # Entering Psychrometrics
    P_sat_in = get_p_sat(Tin)
    P_vapor_in = RHin * P_sat_in
    W_in = 0.62194 * P_vapor_in / (Patm - P_vapor_in)
    GrainsIn = W_in * 7000.0
    DP_in = get_dew_point(P_vapor_in)

    v_in = 0.3704 * (Tin + 459.67) * (1.0 + 1.6078 * W_in) / Patm
    m_da = (CFM * 60.0) / v_in

    # Fleet Capacity Derate (20-Ton modeled strictly off submittal limits)
    if unit_selection == "20-Ton Unit (SACP20A-HS)":
        Q_total = Q_nominal * 0.85
    else:
        if Toutdoor >= 95.0:
            Q_total = Q_nominal * 0.55  
        else:
            Q_total = Q_nominal * 0.65

    # Universal Field-Tuned Sensible Heat Ratio (SHR) Curve
    if DP_in <= T_coil:
        SHR = 1.0  
    else:
        SHR = 0.700 - (0.002268 * GrainsIn)
        SHR = max(0.24, min(0.85, SHR))  

    Q_sensible = Q_total * SHR
    Q_latent = Q_total * (1.0 - SHR)

    # Enthalpy Governor & Energy Balances
    h_in = Cp * Tin + W_in * (hfg + 0.444 * Tin)
    h_out_target = h_in - (Q_total / m_da)

    Tout_theoretical = Tin - (Q_sensible / (m_da * Cp))
    W_out_theoretical = max(0.0, W_in - (Q_latent / (m_da * hfg)))
    
    P_sat_theoretical = get_p_sat(Tout_theoretical)
    P_vapor_theoretical = (W_out_theoretical * Patm) / (0.62194 + W_out_theoretical)
    
    minimum_leaving_temp = T_coil + 3.0

    if Tout_theoretical < minimum_leaving_temp or P_vapor_theoretical > (P_sat_theoretical * 0.95):
        T_search = Tin
        h_search = h_in
        
        while h_search > h_out_target and T_search > minimum_leaving_temp:
            T_search -= 0.1
            P_sat_search = get_p_sat(T_search)
            P_vapor_search = P_sat_search * 0.95
            W_search = 0.62194 * P_vapor_search / (Patm - P_vapor_search)
            h_search = Cp * T_search + W_search * (hfg + 0.444 * T_search)
            
        Tout = T_search
        W_out = W_search
    else:
        Tout = Tout_theoretical
        W_out = W_out_theoretical

    # =========================================================
    # FINAL OUTLET PSYCHROMETRICS RESOLUTION (5 Target Variables)
    # =========================================================
    
    # 1. Specific Humidity
    GrainsOut = W_out * 7000.0            
    Specific_Humidity = W_out             

    # 2. Dry Bulb Temperature
    Dry_Bulb = Tout                       

    # 3. Relative Humidity
    P_vapor_out = (W_out * Patm) / (0.62194 + W_out)
    P_sat_out = get_p_sat(Tout)
    if P_sat_out > 0:
        Relative_Humidity = max(0.0, min(1.0, P_vapor_out / P_sat_out)) * 100.0
    else:
        Relative_Humidity = 0.0

    # 4. Dew Point Temperature
    Dew_Point = get_dew_point(P_vapor_out)

    # 5. Specific Enthalpy (BTU/lb)
    Specific_Enthalpy = Cp * Tout + W_out * (hfg + 0.444 * Tout)

    return {
        "Unit": unit_selection,
        "Airflow": CFM,
        "Dry_Bulb": Dry_Bulb,
        "Relative_Humidity": Relative_Humidity,
        "Dew_Point": Dew_Point,
        "Specific_Humidity_lb": Specific_Humidity,
        "Specific_Humidity_Grains": GrainsOut,
        "Specific_Enthalpy": Specific_Enthalpy
    }