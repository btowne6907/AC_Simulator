import streamlit as st
import ac_engine  

# 1. Page Configuration
st.set_page_config(page_title="Industrial Climate Simulator", layout="wide")

st.title("ERS AC Simulator")
st.subheader("Created by Brian Towne")

# 2. Layout Structure: Inputs (Left) and Outputs (Right)
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Ambient Inputs")
    
    # Equipment Selection
    unit_options = [
        "10-Ton Unit (SACP12A-HS)",
        "20-Ton Unit (SACP20A-HS)",
        "30-Ton Unit (SACP30A-HS)",
        "40-Ton Unit (SACP40A-HS)",
        "60-Ton Unit (SACP60A-HS)",
        "80-Ton Unit (SACP80A-HS)"
    ]
    selected_unit = st.selectbox("Select Equipment Size", unit_options, index=3) 
    
    # Sliders for ambient conditions
    tin = st.slider("Entering Air Temperature (°F)", min_value=60.0, max_value=110.0, value=85.0, step=0.5)
    rhin = st.slider("Entering Relative Humidity (%)", min_value=10.0, max_value=100.0, value=70.0, step=1.0)
    toutdoor = st.number_input("Outdoor Condenser Temperature (°F)", value=85.0, step=1.0)
    
    # Custom Airflow Override
    custom_cfm = st.number_input("Custom Airflow (CFM) - Leave at 0 for Machine Default", value=0, step=100)
    if custom_cfm == 0:
        custom_cfm = None

    run_sim = st.button("Calculate Discharge State", type="primary")

with col2:
    st.header("Discharge Psychrometrics")
    
    if run_sim:
        # Pass the UI inputs into the universal math engine
        results = ac_engine.simulate_smart_family_ac(selected_unit, tin, rhin, toutdoor, custom_cfm)
        
        if results:
            # Display results in clean dashboard metric cards
            st.markdown(f"**Operating Airflow:** {results['Airflow']:,} CFM")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(label="Leaving Temp", value=f"{results['Tout']:.2f} °F")
            m2.metric(label="Leaving RH", value=f"{results['RHout']:.1f} %")
            m3.metric(label="Leaving Dew Point", value=f"{results['DPout']:.2f} °F")
            m4.metric(label="Moisture Load", value=f"{results['GrainsOut']:.1f} gr/lb")
            
            st.divider()
            
            # General Operational Feedback
            temperature_drop = tin - results['Tout']
            
            if results['RHout'] >= 90.0:
                st.info("💧 **Latent-Heavy Operation:** The unit is operating near full saturation. A significant portion of the machine's capacity is dedicated to dehumidification.")
            elif temperature_drop > 25.0:
                st.success("❄️ **Sensible-Heavy Operation:** The unit is driving a massive temperature drop. Ideal for strict space cooling or high sensible heat loads.")
            else:
                st.success("✅ **Standard Operation:** The unit is providing a balanced sensible and latent cooling split.")
                
        else:
            st.error("Simulation failed. Please check the engineering catalog inputs.")
    else:
        st.info("Adjust the ambient parameters on the left and click 'Calculate Discharge State' to evaluate the unit's performance.")