import streamlit as st

col1, col2, col3 = st.columns([1,2,1])

with col2:

    st.image(
        "homerpage.gif",
        use_container_width=True
    )
