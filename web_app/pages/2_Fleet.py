import streamlit as st
import utils
import datetime
import pandas as pd
import importlib
import sys
from src.utils.i18n import _

# Initialize
root_dir = utils.init_path()
utils.set_page_config("Fleet Management", "🚚")
utils.inject_custom_css()

# Imports
from src.data import vehicle_manager as vm_mod
from src.data import driver_manager as dm_mod
import importlib
importlib.reload(vm_mod)
importlib.reload(dm_mod)
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager
from src.data.document_manager import DocumentManager
from src.data.maintenance_manager import MaintenanceManager
from src.services.resource_service import ResourceService

svc = ResourceService()

vehicle_manager = VehicleManager()
driver_manager = DriverManager()
doc_manager = DocumentManager()
mnt_manager = MaintenanceManager()



def vehicle_tab():
    st.subheader("🚛 " + _("Vehicles"))
    
    # Quick Stats
    vehicles = vehicle_manager.get_all_vehicles()
    active_v = [v for v in vehicles if v['status'] == 'active']
    st.info(_("Currently managing") + f" **{len(vehicles)}** " + _("vehicles") + f" (**{len(active_v)}** " + _("active") + ").")

    # Add Vehicle Form (Expander)
    with st.expander("➕ " + _("Add New Vehicle")):
        with st.form("add_vehicle"):
            col1, col2 = st.columns(2)
            v_name = col1.text_input(_("Brand/Name (e.g. Ford Transit)"))
            v_reg = col2.text_input(_("Registration Plate"))
            v_status = st.selectbox(_("Current Status"), options=vehicle_manager.VALID_STATUSES, format_func=lambda x: _(x))
            
            st.write("--- " + _("Expiry Dates") + " ---")
            c1, c2, c3, c4 = st.columns(4)
            rca = c1.date_input(_("RCA Expiry"))
            itp = c2.date_input(_("ITP Expiry"))
            rov = c3.date_input(_("Rovinieta Expiry"))
            cas = c4.date_input(_("Casco Expiry"))
            
            st.write("--- " + _("Initial Stats") + " ---")
            s_col1, s_col2 = st.columns(2)
            v_mil = s_col1.number_input(_("Current Mileage (km)"), min_value=0, value=0)
            v_gen = s_col2.number_input(_("Generator Hours"), min_value=0.0, value=0.0)
            
            if st.form_submit_button(_("Save Vehicle")):
                if v_name and v_reg:
                    res = vehicle_manager.add_vehicle(v_name, v_reg, v_status, rca, itp, rov, cas, mileage=v_mil, generator_hours=v_gen)
                    if res:
                        st.success(_("Vehicle") + f" {v_reg} " + _("saved successfully!"))
                        st.rerun()
                else:
                    st.error(_("Name and Registration are required."))

    # List Vehicles with Actions
    if vehicles:
        for vehicle in vehicles:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1, 1.5])
                col1.write(f"**{vehicle['name']}**")
                col2.write(vehicle['registration'])
                col3.write(_(vehicle['status']))
                
                # Action buttons
                if col4.button(_("Details"), key=f"det_veh_{vehicle['id']}"):
                    st.session_state.editing_vehicle = vehicle['id']
                
                if col5.button("🗑️", key=f"del_veh_{vehicle['id']}"):
                    if vehicle_manager.delete_vehicle(vehicle['id']):
                        st.toast(_("Vehicle") + f" {vehicle['name']} " + _("deleted!"))
                        st.rerun()

    # Detailed View / Edit for Vehicle
    if st.session_state.get('editing_vehicle'):
        veh_id = st.session_state.editing_vehicle
        veh = vehicle_manager.get_vehicle(veh_id)
        if veh:
            st.divider()
            st.subheader(f"🛠️ " + _("Details") + f": {veh['name']}")
            
            # === STATUS CHANGE SECTION (Completely separate) ===
            with st.expander("⚙️ " + _("Change Vehicle Status"), expanded=False):
                st.write("**" + _("Current Status") + f"**: {_(veh.get('status', 'active'))}")
                
                status_options = ["active", "maintenance", "defective", "inactive"]
                current_status = veh.get('status', 'active').lower()
                
                new_status = st.selectbox(_("New Status"), status_options, 
                                         index=status_options.index(current_status) if current_status in status_options else 0,
                                         format_func=lambda x: _(x), key="change_vehicle_status")
                
                status_changed = new_status != current_status
                
                if status_changed:
                    st.warning(f"⚠️ " + _("Changing from") + f" **{_(current_status)}** → **{_(new_status)}**")
                    sc_col1, sc_col2 = st.columns(2)
                    status_change_date = sc_col1.date_input(_("Effective Date"), value=datetime.date.today(), key="v_sc_date")
                    status_change_time = sc_col2.time_input(_("Effective Time"), value=datetime.datetime.now().time(), key="v_sc_time")
                    status_note = st.text_area(_("Reason for change"), placeholder=_("Why is the status changing?"), key="v_sc_note")
                    
                    if st.button("✅ " + _("Apply Status Change"), type="primary", use_container_width=True, key="apply_vehicle_status_change"):
                        eff_datetime = datetime.datetime.combine(status_change_date, status_change_time)
                        
                        # Use manager to update status and history
                        res = vehicle_manager.update_vehicle(
                            veh_id, 
                            status=new_status, 
                            status_note=status_note,
                            status_date=eff_datetime
                        )
                        
                        if res:
                            # Check for campaign impacts
                            if new_status in ['maintenance', 'defective', 'inactive']:
                                impacts = svc.get_impacted_campaigns('vehicle', veh_id, status_change_date)
                                if impacts:
                                    st.session_state.impacted_vehicle_id = veh_id
                                    st.session_state.impacted_list = impacts
                                    st.session_state.status_change_date = status_change_date
                                    st.session_state.old_status = current_status
                                    st.session_state.new_status = new_status
                                    st.warning(_("⚠️ Status changed! Campaigns affected - see below."))
                                    st.rerun()
                                else:
                                    st.success(_("Status changed successfully!"))
                                    st.rerun()
                            else:
                                st.success(_("Status changed successfully!"))
                                st.rerun()
                        else:
                            st.error(_("Failed to change status"))
                else:
                    st.info(_("Select a different status to make a change"))
            
            st.markdown("---")
            
            # === VEHICLE DETAILS FORM ===
            with st.form("edit_vehicle_detailed"):
                st.write("**" + _("Vehicle Information") + "**")
                v_col1, v_col2 = st.columns(2)
                v_name = v_col1.text_input(_("Name"), value=veh['name'])
                v_reg = v_col2.text_input(_("Registration"), value=veh['registration'])
                
                # Driver Assignment
                drivers = driver_manager.get_all_drivers()
                d_names = [_("None")] + [d['name'] for d in drivers]
                d_ids = [None] + [d['id'] for d in drivers]
                
                current_d_idx = 0
                if veh.get('driver_id') and veh['driver_id'] in d_ids:
                    current_d_idx = d_ids.index(veh['driver_id'])
                
                v_driver = v_col2.selectbox(_("Assigned Driver"), options=d_names, index=current_d_idx)
                v_driver_id = d_ids[d_names.index(v_driver)]
                
                st.write("**" + _("Expiry Dates") + "**")
                e1, e2, e3, e4 = st.columns(4)
                rca_v = e1.date_input(_("RCA"), value=datetime.date.fromisoformat(veh['rca_expiry']) if veh.get('rca_expiry') else datetime.date.today())
                itp_v = e2.date_input(_("ITP"), value=datetime.date.fromisoformat(veh['itp_expiry']) if veh.get('itp_expiry') else datetime.date.today())
                rov_v = e3.date_input(_("Rovinieta"), value=datetime.date.fromisoformat(veh['rov_expiry']) if veh.get('rov_expiry') else datetime.date.today())
                cas_v = e4.date_input(_("Casco"), value=datetime.date.fromisoformat(veh['casco_expiry']) if veh.get('casco_expiry') else datetime.date.today())

                st.write("**" + _("Stats") + "**")
                s_col1, s_col2 = st.columns(2)
                v_mil = s_col1.number_input(_("Mileage (km)"), value=int(veh.get('mileage', 0)))
                v_gen = s_col2.number_input(_("Generator Hours"), value=float(veh.get('generator_hours', 0.0)))

                if st.form_submit_button(_("💾 Save Vehicle Details"), use_container_width=True):
                    # Update vehicle info (NOT status - that's handled separately)
                    vehicle_manager.update_vehicle(
                        veh_id, name=v_name, registration=v_reg,
                        rca_expiry=rca_v, itp_expiry=itp_v, rovinieta_expiry=rov_v, casco_expiry=cas_v,
                        mileage=v_mil, generator_hours=v_gen
                    )
                    
                    # Handle driver assignment
                    if v_driver_id != veh.get('driver_id'):
                        # Unassign old driver if any
                        if veh.get('driver_id'):
                            driver_manager.assign_to_vehicle(veh['driver_id'], None)
                        
                        # Assign new driver if any
                        if v_driver_id:
                            vehicle_manager.assign_driver(veh_id, v_driver_id, v_driver)
                            driver_manager.assign_to_vehicle(v_driver_id, veh_id, v_name)
                        else:
                            vehicle_manager.assign_driver(veh_id, None, None)
                            
                    st.success(_("Vehicle details updated!"))
                    st.rerun()
            
            if st.button(_("Close"), key="close_veh_edit"):
                st.session_state.editing_vehicle = None
                if 'impacted_vehicle_id' in st.session_state: del st.session_state.impacted_vehicle_id
                st.rerun()
            
            # --- Impact Alert (Modal-ish) ---
            if st.session_state.get('impacted_vehicle_id') == veh_id and st.session_state.get('impacted_list'):
                st.markdown("---")
                old_st = st.session_state.get('old_status', 'unknown')
                new_st = st.session_state.get('new_status', veh.get('status'))
                st.error(f"⚠️ **{_('Warning')}**: " + _("Status changed from") + f" **{_(old_st)}** → **{_(new_st)}**. " + _("Active/future campaigns are affected!"))
                st.write(f"**{len(st.session_state.impacted_list)}** " + _("campaigns affected") + ":")
                for c in st.session_state.impacted_list[:5]:
                    st.caption(f"- {c['name']} ({c['client']}) - Ends: {c['end']}")
                if len(st.session_state.impacted_list) > 5: st.caption("...")
                
                st.write(_("Do you want to transfer these campaigns to another vehicle?"))
                
                # Replacement Form Inline
                with st.form("impact_replace_form"):
                     # Filter out restricted vehicle
                    avail_vehicles = {v['id']: v['name'] for v in vehicle_manager.get_all_vehicles() if v['id'] != veh_id and v['status'] == 'active'}
                    
                    if not avail_vehicles:
                        st.warning(_("No active vehicles available for replacement!"))
                        if st.form_submit_button(_("❌ Close Warning")):
                            del st.session_state.impacted_vehicle_id
                            del st.session_state.impacted_list
                            if 'old_status' in st.session_state: del st.session_state.old_status
                            if 'new_status' in st.session_state: del st.session_state.new_status
                            st.rerun()
                    else:
                        rep_veh_id = st.selectbox(_("Select Replacement Vehicle"), options=list(avail_vehicles.keys()), format_func=lambda x: avail_vehicles[x])
                        rep_date = st.date_input(_("Effective Date"), value=st.session_state.get('status_change_date', datetime.date.today()))
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button(_("✅ Replace & Transfer")):
                        cnt = svc.replace_vehicle_globally(veh_id, rep_veh_id, rep_date)
                        st.success(f"{cnt} " + _("campaigns transferred successfully."))
                        del st.session_state.impacted_vehicle_id
                        del st.session_state.impacted_list
                        if 'status_change_date' in st.session_state: del st.session_state.status_change_date
                        if 'old_status' in st.session_state: del st.session_state.old_status
                        if 'new_status' in st.session_state: del st.session_state.new_status
                        st.rerun()
                        
                    if c2.form_submit_button(_("❌ Ignore & Keep Defective")):
                        del st.session_state.impacted_vehicle_id
                        del st.session_state.impacted_list
                        if 'status_change_date' in st.session_state: del st.session_state.status_change_date
                        if 'old_status' in st.session_state: del st.session_state.old_status
                        if 'new_status' in st.session_state: del st.session_state.new_status
                        st.rerun()
            
            # --- Status History ---
            st.markdown("#### 📜 " + _("Status History"))
            history = vehicle_manager.get_status_history(veh_id)
            
            if history:
                st.caption(_("Click on a history entry to edit or delete it"))
                for idx, h_entry in enumerate(sorted(history, key=lambda x: x.get('date', ''), reverse=True)):
                    with st.container(border=True):
                        hcol1, hcol2, hcol3, hcol4, hcol5 = st.columns([2, 2, 3, 1, 1])
                        hcol1.write(f"**{_(h_entry['status'])}**")
                        hcol2.write(f"📅 {h_entry.get('date', 'N/A')}")
                        hcol3.write(f"📝 {h_entry.get('note', '-')}")
                        
                        # Edit button
                        if hcol4.button("✏️", key=f"edit_vh_{idx}"):
                            st.session_state.editing_vehicle_history = h_entry.get('id')
                            st.rerun()
                        
                        # Delete button
                        if hcol5.button("🗑️", key=f"del_vh_{idx}"):
                            from src.data.db_config import SessionLocal
                            from src.data.models import VehicleStatusHistory, Vehicle
                            session = SessionLocal()
                            try:
                                entry_to_delete = session.query(VehicleStatusHistory).filter(
                                    VehicleStatusHistory.id == h_entry.get('id')
                                ).first()
                                if entry_to_delete:
                                    session.delete(entry_to_delete)
                                    session.commit()
                                    
                                    # Update vehicle status to the most recent remaining history entry
                                    vehicle = session.query(Vehicle).filter(Vehicle.id == veh_id).first()
                                    if vehicle:
                                        remaining_history = session.query(VehicleStatusHistory).filter(
                                            VehicleStatusHistory.vehicle_id == veh_id
                                        ).order_by(VehicleStatusHistory.date.desc()).first()
                                        
                                        if remaining_history:
                                            vehicle.status = remaining_history.status
                                        else:
                                            # No history left, default to active
                                            vehicle.status = 'active'
                                        
                                        session.commit()
                                    
                                    st.success(_("History entry deleted! Vehicle status updated."))
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete: {e}")
                                session.rollback()
                            finally:
                                session.close()
                
                # Edit form for history entry
                if st.session_state.get('editing_vehicle_history'):
                    edit_h_id = st.session_state.editing_vehicle_history
                    edit_entry = next((h for h in history if h.get('id') == edit_h_id), None)
                    
                    if edit_entry:
                        st.markdown("---")
                        st.write("**" + _("Edit History Entry") + "**")
                        with st.form("edit_vehicle_history_form"):
                            eh_col1, eh_col2 = st.columns(2)
                            eh_status = eh_col1.selectbox(_("Status"), status_options, 
                                                         index=status_options.index(edit_entry['status']) if edit_entry['status'] in status_options else 0,
                                                         format_func=lambda x: _(x))
                            
                            # Parse existing date
                            try:
                                existing_dt = datetime.datetime.fromisoformat(str(edit_entry['date']))
                                eh_date = existing_dt.date()
                                eh_time = existing_dt.time()
                            except:
                                eh_date = datetime.date.today()
                                eh_time = datetime.datetime.now().time()
                            
                            eh_date_input = eh_col1.date_input(_("Date"), value=eh_date)
                            eh_time_input = eh_col2.time_input(_("Time"), value=eh_time)
                            eh_note = st.text_area(_("Note"), value=edit_entry.get('note', ''))
                            
                            ecol1, ecol2 = st.columns(2)
                            if ecol1.form_submit_button(_("💾 Save")):
                                from src.data.db_config import SessionLocal
                                from src.data.models import VehicleStatusHistory
                                session = SessionLocal()
                                try:
                                    entry_to_update = session.query(VehicleStatusHistory).filter(
                                        VehicleStatusHistory.id == edit_h_id
                                    ).first()
                                    if entry_to_update:
                                        entry_to_update.status = eh_status
                                        entry_to_update.date = datetime.datetime.combine(eh_date_input, eh_time_input)
                                        entry_to_update.note = eh_note
                                        session.commit()
                                        st.success(_("History updated!"))
                                        del st.session_state.editing_vehicle_history
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update: {e}")
                                    session.rollback()
                                finally:
                                    session.close()
                            
                            if ecol2.form_submit_button(_("❌ Cancel")):
                                del st.session_state.editing_vehicle_history
                                st.rerun()
            else:
                st.info("No status history yet.")
                    
            # --- Maintenance & Revisions ---
            st.markdown("#### 🛠️ " + _("Maintenance & Revisions"))
            m_records = mnt_manager.get_records('vehicle', veh_id)
            
            if m_records:
                for r in m_records:
                    with st.container(border=True):
                        m_c1, m_c2, m_c3 = st.columns([2, 3, 2])
                        m_c1.write(f"**{_(r['service_type'])}**")
                        m_c1.caption(f"📅 {r['created_at'][:10]}")
                        
                        # Display stats
                        stats = []
                        if r['current_km']: stats.append(f"🚗 {r['current_km']} km")
                        if r['current_hours']: stats.append(f"⚡ {r['current_hours']} h")
                        m_c2.write(" | ".join(stats))
                        
                        # Expiry warnings
                        exp_msg = []
                        if r['expiry_date']: exp_msg.append(f"📅 Exp: {r['expiry_date']}")
                        if r['expiry_km']: exp_msg.append(f"🚗 Next: {r['expiry_km']} km")
                        if r['expiry_hours']: exp_msg.append(f"⚡ Next: {r['expiry_hours']} h")
                        m_c2.caption(" | ".join(exp_msg))
                        
                        if r['notes']:
                            m_c2.info(r['notes'], icon="📝")
            else:
                st.info(_("No maintenance records yet."))
            
            with st.expander("➕ " + _("Add Maintenance Record")):
                with st.form(f"add_mnt_{veh_id}"):
                    m_type = st.selectbox(_("Service Type"), ["Revision", "Oil Change", "Generator Service", "Brakes", "Tires", "General", "Repair", "Other"])
                    mc_1, mc_2 = st.columns(2)
                    m_km = mc_1.number_input(_("Current Mileage (km)"), value=int(veh.get('mileage', 0)), min_value=0)
                    m_hr = mc_2.number_input(_("Current Generator Hours"), value=float(veh.get('generator_hours', 0.0)), min_value=0.0)
                    
                    st.write("**" + _("Next Service (Expiry)") + "**")
                    me_1, me_2, me_3 = st.columns(3)
                    m_exp_d = me_1.date_input(_("Expiry Date"), value=None)
                    m_exp_k = me_2.number_input(_("Expiry Mileage (km)"), value=0)
                    m_exp_h = me_3.number_input(_("Expiry Hours"), value=0.0)
                    
                    m_note = st.text_area(_("Notes"))
                    
                    if st.form_submit_button(_("Log Maintenance")):
                        mnt_manager.add_record(
                            'vehicle', veh_id, m_type,
                            current_km=m_km, current_hours=m_hr,
                            expiry_date=m_exp_d if m_exp_d else None,
                            expiry_km=m_exp_k if m_exp_k > 0 else None,
                            expiry_hours=m_exp_h if m_exp_h > 0 else None,
                            notes=m_note
                        )
                        # Also update vehicle primary stats
                        vehicle_manager.update_vehicle(veh_id, mileage=m_km, generator_hours=m_hr)
                        st.success(_("Maintenance record logged!"))
                        st.rerun()

            # --- Additional Documents & Copies ---
            st.markdown("#### 📂 " + _("Documents & Copies"))
            other_docs = doc_manager.get_documents('vehicle', veh_id)
            if other_docs:
                for d in other_docs:
                    with st.container(border=True):
                        d_cols = st.columns([3, 2, 2, 1])
                        d_cols[0].write(f"**{d['document_type']}**")
                        if d['custom_type_name']: d_cols[0].caption(d['custom_type_name'])
                        
                        d_cols[1].write(f"Exp: {d['expiry_date'] or 'N/A'}")
                        
                        # Status with color
                        status = d['status']
                        if status == 'expired': d_cols[2].error(_(status).upper())
                        elif status == 'expiring': d_cols[2].warning(_(status).upper())
                        else: d_cols[2].success(_(status).upper())
                        
                        # Download link if file exists
                        if d.get('file_path'):
                            full_path = doc_manager.get_document_file_path(d['id'])
                            if full_path and os.path.exists(full_path):
                                with open(full_path, "rb") as file:
                                    d_cols[0].download_button(
                                        label="💾 " + _("Download Copy"),
                                        data=file,
                                        file_name=d['file_name'],
                                        mime="application/octet-stream",
                                        key=f"dl_{d['id']}"
                                    )
                        
                        if d_cols[3].button("🗑️", key=f"del_doc_{d['id']}"):
                            doc_manager.delete_document(d['id'])
                            st.rerun()
            else:
                st.info(_("No additional documents uploaded."))
            
            with st.expander("➕ " + _("Upload/Add Document")):
                with st.form("add_doc_veh_enhanced"):
                    d_type = st.selectbox(_("Type"), doc_manager.VEHICLE_TYPES)
                    d_custom = st.text_input(_("Custom Type Name (if 'Custom' selected)"))
                    
                    dc_1, dc_2 = st.columns(2)
                    d_issue = dc_1.date_input(_("Issue Date"), value=None)
                    d_exp = dc_2.date_input(_("Expiry Date"), value=None)
                    
                    d_file = st.file_uploader(_("Upload Copy (PDF, JPG, PNG)"), type=['pdf', 'jpg', 'jpeg', 'png'])
                    d_notes = st.text_area(_("Notes"))
                    
                    if st.form_submit_button(_("Save Document")):
                        temp_path = None
                        if d_file:
                            # Save temp file for manager to process
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(d_file.name)[1]) as tmp:
                                tmp.write(d_file.getvalue())
                                temp_path = tmp.name
                        
                        doc_manager.add_document(
                            'vehicle', veh_id, d_type, 
                            expiry_date=d_exp if d_exp else None,
                            issue_date=d_issue if d_issue else None,
                            custom_type_name=d_custom,
                            notes=d_notes,
                            file_path=temp_path
                        )
                        
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)
                            
                        st.success(_("Document added successfully!"))
                        st.rerun()

def driver_tab():
    st.subheader("👤 " + _("Drivers"))
    
    drivers = driver_manager.get_all_drivers()
    
    # Add Driver Form (Expander)
    with st.expander("➕ " + _("Add New Driver")):
        with st.form("add_driver"):
            col1, col2 = st.columns(2)
            d_name = col1.text_input(_("Full Name"))
            d_phone = col2.text_input(_("Phone Number"))
            d_status = st.selectbox(_("Current Status"), options=["active", "vacation", "medical", "inactive"], format_func=lambda x: _(x))
            
            if st.form_submit_button(_("Save Driver")):
                if d_name:
                    res = driver_manager.add_driver(d_name, d_phone, d_status)
                    if res:
                        st.success(_("Driver") + f" {d_name} " + _("saved successfully!"))
                        st.rerun()
                else:
                    st.error(_("Name is required."))
    
    # List Drivers with Actions
    if drivers:
        for driver in drivers:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
                col1.write(f"**{driver['name']}**")
                col2.write(driver['phone'])
                col3.write(_(driver['status']))
                
                if col4.button(_("Details"), key=f"det_drv_{driver['id']}"):
                    st.session_state.editing_driver = driver['id']
                
                if col5.button("🗑️", key=f"del_dr_{driver['id']}"):
                    if driver_manager.delete_driver(driver['id']):
                        st.toast(_("Driver") + f" {driver['name']} " + _("deleted!"))
                        st.rerun()
                    else:
                        st.error("Cannot delete assigned driver!")

    # Detailed View / Edit for Driver
    if st.session_state.get('editing_driver'):
        dr_id = st.session_state.editing_driver
        dr = driver_manager.get_driver(dr_id)
        if dr:
            st.divider()
            st.subheader(f"🛠️ " + _("Details") + f": {dr['name']}")
            
            with st.form("edit_driver_detailed"):
                d_col1, d_col2 = st.columns(2)
                d_name = d_col1.text_input(_("Name"), value=dr['name'])
                d_phone = d_col2.text_input(_("Phone Number"), value=dr.get('phone', ''))
                
                # Robust index finding
                status_options = ["active", "vacation", "medical", "inactive"]
                current_status = dr.get('status', 'active').lower()
                status_index = status_options.index(current_status) if current_status in status_options else 0
                d_stat = d_col1.selectbox(_("Status"), options=status_options, index=status_index, format_func=lambda x: _(x))
                
                # Status change date/time (only show if status is changing)
                d_status_changed = d_stat != current_status
                if d_status_changed:
                    st.info(_("Status is changing. Please specify when this change takes effect:"))
                    dsc_col1, dsc_col2 = st.columns(2)
                    d_status_change_date = dsc_col1.date_input(_("Effective Date"), value=datetime.date.today(), key="d_status_date")
                    d_status_change_time = dsc_col2.time_input(_("Effective Time"), value=datetime.datetime.now().time(), key="d_status_time")
                    d_status_note = st.text_area(_("Note (optional)"), placeholder=_("Reason for status change..."), key="d_status_note")
                
                if st.form_submit_button(_("Save Changes")):
                    if d_status_changed:
                        d_eff_datetime = datetime.datetime.combine(
                            st.session_state.get('d_status_date', datetime.date.today()),
                            st.session_state.get('d_status_time', datetime.datetime.now().time())
                        )
                        d_note_text = st.session_state.get('d_status_note', '')
                    else:
                        d_eff_datetime = None
                        d_note_text = None
                    
                    res = driver_manager.update_driver(
                        dr_id, 
                        name=d_name, 
                        phone=d_phone, 
                        status=d_stat,
                        status_note=d_note_text,
                        status_date=d_eff_datetime
                    )
                    
                    if res:
                        st.success(_("Driver updated!"))
                        st.rerun()

            if st.button(_("Close"), key="close_dr_edit"):
                st.session_state.editing_driver = None
                st.rerun()

            # --- Status History ---
            st.markdown("#### 📜 " + _("Status History"))
            d_history = driver_manager.get_status_history(dr_id)
            if d_history:
                df_dh = pd.DataFrame(d_history)
                df_dh['status'] = df_dh['status'].apply(lambda x: _(x))
                df_dh = df_dh.sort_values('date', ascending=False)
                st.table(df_dh)
            else:
                st.info("No status history yet.")

            # --- Leave & Schedule Management ---
            st.markdown("#### " + _("Leave & Schedule Management"))
            st.info(_("Manage vacation, medical leave, etc."))
            
            with st.expander("➕ " + _("Add Leave / Schedule Event")):
                with st.form("add_driver_leave"):
                    l_type = st.selectbox(_("Type"), ["vacation", "medical", "unpaid", "free", "other"], format_func=lambda x: _(x))
                    lc1, lc2 = st.columns(2)
                    l_start = lc1.date_input(_("Start Date"))
                    l_end = lc2.date_input(_("End Date"))
                    l_det = st.text_area(_("Details (Optional)"))
                    if st.form_submit_button(_("Save Leave")):
                        if l_start <= l_end:
                            driver_manager.add_driver_schedule(dr_id, l_start, l_end, l_type, l_det)
                            st.success("Leave record added!")
                            st.rerun()
                        else:
                            st.error(_("Start date must be before end date."))

            # List existing leave/schedules
            d_schs = driver_manager.get_driver_schedules(dr_id)
            if d_schs:
                for s in d_schs:
                    sc1, sc2, sc3 = st.columns([2, 3, 1])
                    sc1.write(f"**{_(s['event_type']).upper()}**")
                    sc2.write(f"{s['start_date']} to {s['end_date']}")
                    if sc3.button("🗑️", key=f"del_dsch_{s['id']}"):
                        driver_manager.delete_driver_schedule(s['id'])
                        st.rerun()

            # Documents & Equipment via DocumentManager
            st.markdown("#### 📜 " + _("Documents & Equipment"))
            d_docs = doc_manager.get_documents('driver', dr_id)
            if d_docs:
                for d in d_docs:
                    with st.container(border=True):
                        d_cols = st.columns([3, 2, 2, 1])
                        d_cols[0].write(f"**{d['document_type']}**")
                        if d['custom_type_name']: d_cols[0].caption(d['custom_type_name'])
                        
                        d_cols[1].write(f"Exp: {d['expiry_date'] or 'N/A'}")
                        
                        status = d['status']
                        if status == 'expired': d_cols[2].error(_(status).upper())
                        elif status == 'expiring': d_cols[2].warning(_(status).upper())
                        else: d_cols[2].success(_(status).upper())
                        
                        # Download link if file exists
                        if d.get('file_path'):
                            full_path = doc_manager.get_document_file_path(d['id'])
                            if full_path and os.path.exists(full_path):
                                with open(full_path, "rb") as file:
                                    d_cols[0].download_button(
                                        label="💾 " + _("Download Copy"),
                                        data=file,
                                        file_name=d['file_name'],
                                        mime="application/octet-stream",
                                        key=f"dl_dr_{d['id']}"
                                    )
                                    
                        if d_cols[3].button("🗑️", key=f"del_drv_doc_{d['id']}"):
                            doc_manager.delete_document(d['id'])
                            st.rerun()
            else:
                st.info(_("No driver documents uploaded."))
            
            with st.expander("➕ " + _("Add Document / Equipment")):
                with st.form("add_doc_drv_enhanced"):
                    d_type = st.selectbox(_("Type"), doc_manager.DRIVER_TYPES)
                    d_custom = st.text_input(_("Custom Type Name (if 'Custom' selected)"))
                    dc_1, dc_2 = st.columns(2)
                    d_issue = dc_1.date_input(_("Issue Date"), value=None)
                    d_exp = dc_2.date_input(_("Expiry Date"), value=None)
                    
                    d_file = st.file_uploader(_("Upload Copy (PDF, JPG, PNG)"), type=['pdf', 'jpg', 'jpeg', 'png'], key="drv_doc_file")
                    d_notes = st.text_area(_("Notes"))
                    
                    if st.form_submit_button(_("Save Document")):
                        temp_path = None
                        if d_file:
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(d_file.name)[1]) as tmp:
                                tmp.write(d_file.getvalue())
                                temp_path = tmp.name
                        
                        doc_manager.add_document(
                            'driver', dr_id, d_type, 
                            expiry_date=d_exp if d_exp else None,
                            issue_date=d_issue if d_issue else None,
                            custom_type_name=d_custom,
                            notes=d_notes,
                            file_path=temp_path
                        )
                        
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)
                            
                        st.success(_("Document added successfully!"))
                        st.rerun()

def schedule_tab():
    st.subheader(_("Global Vehicle Schedules"))
    st.info(_("Manage transit, maintenance, and other events independently of campaigns."))
    
    vehicles = vehicle_manager.get_all_vehicles()
    v_opts = {v['id']: f"{v['name']} ({v['registration']})" for v in vehicles}
    v_ids = list(v_opts.keys())
    
    from src.data.city_data_manager import CityDataManager
    cm = CityDataManager()
    city_list = sorted(cm.get_all_cities())
    
    # Initialize edit state
    if "editing_schedule_id" not in st.session_state:
        st.session_state.editing_schedule_id = None
        
    edit_id = st.session_state.editing_schedule_id
    edit_data = {}
    if edit_id:
        all_s = vehicle_manager.get_vehicle_schedules()
        edit_data = next((s for s in all_s if s['id'] == edit_id), {})

    if st.toggle("➕ " + _("Add Leave / Schedule Event"), value=(edit_id is not None)):
        st.write(f"### " + (_("Edit") if edit_id else _("Add")) + " " + _("Event"))
        with st.form("add_global_schedule_v2"):
            # Helper to find index
            def f_idx(val, opts, default=0):
                try: return opts.index(val)
                except: return default

            col1, col2 = st.columns([2, 1])
            s_vid = col1.selectbox(_("Vehicule"), options=v_ids, format_func=lambda x: v_opts[x], index=f_idx(edit_data.get('vehicle_id'), v_ids))
            s_type_opts = ["transit", "maintenance", "defective", "other"]
            s_type = col2.selectbox(_("Event Type"), s_type_opts, index=f_idx(edit_data.get('type'), s_type_opts), format_func=lambda x: _(x))
            
            c1, c2 = st.columns(2)
            s_start = c1.date_input(_("Start Date"), value=edit_data.get('start', datetime.date.today()))
            s_end = c2.date_input(_("End Date"), value=edit_data.get('end', s_start))
            
            # City Selection for transit
            st.write(_("Cities (required if Transit)"))
            orig_idx = f_idx(edit_data.get('origin'), city_list)
            dest_idx = f_idx(edit_data.get('destination'), city_list)
            
            sc1, sc2 = st.columns(2)
            s_orig = sc1.selectbox(_("Origin City"), options=[_("N/A")] + city_list, index=orig_idx + 1 if edit_data.get('origin') else 0)
            s_dest = sc2.selectbox(_("Destination City"), options=[_("N/A")] + city_list, index=dest_idx + 1 if edit_data.get('destination') else 0)
            
            s_det = st.text_area(_("Additional Details"), value=edit_data.get('details', ""))
            
            btn_col1, btn_col2, empty_col = st.columns([1, 1, 3])
            submitted = btn_col1.form_submit_button("💾 " + _("Save Event"))
            cancelled = btn_col2.form_submit_button(_("Cancel"))
            
            if cancelled:
                st.session_state.editing_schedule_id = None
                st.rerun()
                
            if submitted:
                # If editing, delete old one first (manager doesn't have update_schedule yet)
                if edit_id:
                    vehicle_manager.delete_schedule(edit_id)
                
                res = vehicle_manager.add_schedule(
                    s_vid, s_start, s_end, s_type, 
                    origin_city=s_orig if s_orig != "N/A" else None,
                    destination_city=s_dest if s_dest != "N/A" else None,
                    details=s_det
                )
                if res:
                    st.success("Schedule event saved!")
                    st.session_state.editing_schedule_id = None
                    st.rerun()
                else:
                    st.error("Failed to save event.")

    # List all schedules (aggregated from global + campaigns)
    all_schedules = []
    
    # 1. Global Schedules
    raw_schedules = vehicle_manager.get_vehicle_schedules()
    for s in raw_schedules:
        all_schedules.append({
            'source': 'Global',
            'id': s['id'],
            'vehicle_id': s['vehicle_id'],
            'start': s['start'],
            'end': s['end'],
            'type': s['type'],
            'label': s['type'].upper(),
            'origin': s.get('origin'),
            'destination': s.get('destination')
        })
        
    # 2. Extract from Campaigns
    from src.data.campaign_storage import CampaignStorage
    cs = CampaignStorage()
    all_c = cs.get_all_campaigns()
    for c in all_c:
        for tp in c.get('transit_periods', []):
            all_schedules.append({
                'source': f"Campaign: {c['campaign_name']}",
                'id': f"camp_{c.get('id', 'unk')}_{tp.get('vehicle_id')}", # Virtual ID
                'vehicle_id': tp.get('vehicle_id'),
                'start': tp.get('start'),
                'end': tp.get('end'),
                'type': 'transit',
                'label': "TRANZIT (CAMPANIE)",
                'origin': tp.get('origin'),
                'destination': tp.get('destination'),
                'is_virtual': True
            })

    # 3. Driver Schedules (Leave, etc)
    all_drivers = driver_manager.get_all_drivers()
    drv_map = {d['id']: d['name'] for d in all_drivers}
    for d_id in drv_map:
        d_schs = driver_manager.get_driver_schedules(d_id)
        for ds in d_schs:
            all_schedules.append({
                'source': f"Driver: {drv_map[d_id]}",
                'id': ds['id'],
                'resource_id': d_id,
                'resource_name': drv_map[d_id],
                'start': ds['start_date'],
                'end': ds['end_date'],
                'type': ds['event_type'],
                'label': ds['event_type'].upper(),
                'is_driver': True
            })

    # Sort all by start date
    all_schedules.sort(key=lambda x: str(x['start']), reverse=True)

    if all_schedules:
        st.write(_("Current Events"))
        for s in all_schedules:
            with st.container():
                c1, c2, c3, c_acts = st.columns([2, 1, 3, 1.5])
                
                res_display = v_opts.get(s.get('vehicle_id'), 'Unknown') if not s.get('is_driver') else s.get('resource_name', 'Unknown')
                c1.write(f"**{res_display}**")
                c2.write(f"`{_(s['label'].lower()).upper()}`")
                
                details = f"{s['start']} to {s['end']}"
                if s.get('origin') and s.get('destination'):
                    details += f" ({s['origin']} ➡️ {s['destination']})"
                c3.write(details)
                
                if not s.get('is_virtual'):
                    col_edit, col_delete = c_acts.columns(2)
                    
                    # Edit only for global vehicle schedules for now (driver schedules handled in details)
                    if not s.get('is_driver'):
                        if col_edit.button("✏️", key=f"edit_sch_{s['id']}"):
                            st.session_state.editing_schedule_id = s['id']
                            st.rerun()
                            
                    if col_delete.button("🗑️", key=f"del_sch_{s['id']}"):
                        if s.get('is_driver'):
                            driver_manager.delete_driver_schedule(s['id'])
                        else:
                            vehicle_manager.delete_schedule(s['id'])
                        st.toast("Event deleted")
                        st.rerun()
                else:
                    c_acts.info(f"🔗 {s['source']}")
    else:
        st.info("No schedule events found.")

def main():
    st.title("🚛 " + _("Fleet Management"))
    
    tab1, tab2, tab3 = st.tabs([_("Vehicles"), _("Drivers"), _("Transit & Schedules")])
    
    with tab1:
        vehicle_tab()
    with tab2:
        driver_tab()
    with tab3:
        schedule_tab()

if __name__ == "__main__":
    main()
