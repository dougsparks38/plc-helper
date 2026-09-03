# Casne AOI Reference

Complete parameter documentation for all Add-On Instructions (AOIs) and User-Defined Data Types (UDTs)
Casne has built and reused across jobs. Parameters and members listed in XML source order. All names
copied exactly from the L5X files. Sections are sorted A–Z by name. Each section is tagged with its
source: **Casne** (built/authored in-house, no `Vendor` attribute on the source `AddOnInstructionDefinition`)
or the vendor named in that attribute (e.g. **Rockwell Automation**).

---

## ALARM_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.3. Generic discrete alarm with debounce timer, invert-input support, and latch/reset behavior.
One instance per alarm point; every alarm should map to a FactoryTalk SE/ME alarm trigger.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Alm_TMR_PRE - Alarm debounce timer preset (milliseconds); default 5000
.Disable - Disable the alarm (suppresses alarm output)
.Global_Alm_Reset - Global alarm reset; clears alarm when input clears
.Input - Device Input (alarm trigger bit)
.Invert_Input - is input N/O or N/C (Invert=Yes); 0=alarm on rising edge, 1=alarm on falling edge
.Reset - Resets alarm when Reset_Req is true
.Reset_scdo - Not used in AOI logic; pass-through placeholder for SCADA reset bit
.Reset_Req - When true, alarm latches until reset bit energized
.Alarm - Alarm output bit (latched if Reset_Req is set)
.Alm_TMR_ACC - Alarm debounce timer accumulated value (milliseconds); read-only
.Hwdi - Device Status; pass-through placeholder for the hardware input source
.Alarm_Ack - Alarm acknowledge input

---

## CONSPD4_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 2.4. Constant-speed motor/pump AOI. Provides HOA mode control, fail-to-run alarm, stuck-on runtime alarm,
circuit breaker auxiliary alarm, total and monthly runtime hour tracking, and last start/stop/runtime timestamps.

HOA_STATUS_scai values: -1=Manual, 0=Off, 1=Auto
MOTOR_STATUS_scai values: 0=stopped, 1=running, 2=fault

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.AUTO_hwdi - HOA selector switch is in the auto position (hardware digital input); required
.MAN_hwdi - HOA selector switch is in the manual/hand position (hardware digital input); required
.Running_hwdi - Motor running feedback (hardware digital input); required
.RUN_hwdo - Run command output (hardware digital output); required
.FaultCode_scai - Fault code placeholder (not written by AOI)
.DriveFault_hwdi - Drive fault input (hardware digital input); not used in base logic
.CBAux_hwdi - Circuit breaker auxiliary contact (hardware digital input)
.Disable_Alarms - Disable all alarms
.AUTO_PB_scdo - SCADA Auto mode pushbutton command (SCADA to PLC); momentary, unlatched at end of scan
.MAN_PB_scdo - SCADA Manual mode pushbutton command (SCADA to PLC); momentary, unlatched at end of scan
.AUTO_scdi - SCADA Auto mode status (PLC to SCADA)
.MAN_scdi - SCADA Manual mode status (PLC to SCADA)
.START_scdo - SCADA Start command (SCADA to PLC); momentary, unlatched at end of scan
.STOP_scdo - SCADA Stop command (SCADA to PLC); momentary, unlatched at end of scan
.ENABLE_PB_scdo - SCADA Enable pushbutton (SCADA to PLC)
.DISABLE_PB_scdo - SCADA Disable pushbutton (SCADA to PLC)
.RESETTMR_scdo - Reset runtime timer command (SCADA to PLC)
.CURRENT_Alm_Res - Current alarm reset input
.CURRENT_Alm_scao - Current alarm setpoint in amperes (SCADA to PLC)
.Current_scai - Motor current feedback in amperes (placeholder input, not wired by AOI)
.HOURS_scai - Total lifetime runtime hours (PLC to SCADA)
.Status_scai - Status code placeholder (not written by AOI)
.Prority_scai - Priority code placeholder (not written by AOI)
.AutoCall_scdi - AutoCall demand bit; when true PLC logic requests motor to run
.INTRLK_scdi - Energize to run interlock; must be true for AutoCall to start motor
.AutoCall_INTRLK_scdi - De-energize to run interlock; must be false for AutoCall to start motor
.START_hwdo - Start hardware digital output (auxiliary)
.STOP_hwdo - Stop hardware digital output (auxiliary)
.ENABLE_hwdo - Enable hardware digital output (auxiliary)
.RESET_hwdo - Reset hardware digital output (auxiliary)
.ALRM - General alarm output bit
.ALRM_res - General alarm reset input
.ALRM_dis - Disable general alarm
.ALRM_ack - General alarm acknowledge input
.FAIL_alm - Fail-to-run alarm; PLC called motor to run, and the motor failed to provide running feedback
.FAIL_alm_res - Fail-to-run alarm reset input
.FAIL_alm_dis - Disable fail-to-run alarm
.Fail_Alm_Ack_In - Fail alarm acknowledge input (from alarm server)
.FAIL_alm_ack - Fail-to-run alarm acknowledge input
.Stuck_On_Alm - Pump Stuck on / Runtime Alarm; motor has run longer than Stuck_On_Alm_Time_Setpoint
.Stuck_On_Alm_Time_Setpoint - How long pump should run before triggering stuck-on alarm (minutes); default 60
.Stuck_On_Alm_dis - Disable stuck-on alarm
.Stuck_On_Alm_res - Stuck-on alarm reset input
.CBAux_alm - Circuit breaker auxiliary alarm output
.CBAux_alm_res - CB auxiliary alarm reset input
.CBAux_alm_dis - Disable CB auxiliary alarm
.CBAux_Alm_Ack_In - CB auxiliary alarm acknowledge input (from alarm server)
.CBAux_alm_ack - CB auxiliary alarm acknowledge input
.Current_hwai - Motor current hardware analog input (read by AOI for current monitoring)
.CURRENT_alm_ack - Current alarm acknowledge input
.ALRM_Ack_In - General alarm acknowledge input (from alarm server)
.Ack_All - Acknowledge all alarms
.UnACK_Alm - Unacknowledged alarm present (output)
.State - Motor state output (placeholder)
.RESET_scdo - Reset command (SCADA to PLC)
.MONTH_HOURS_scai - Current month runtime hours (PLC to SCADA)
.PREV_MONTH_HOURS_scai - Previous month runtime hours (PLC to SCADA)
.AUTO_STATUS_scai - Auto mode status code (PLC to SCADA)
.MOTOR_STATUS_scai - Motor status code (PLC to SCADA); 0=stopped, 1=running, 2=fault
.HOA_STATUS_scai - HOA selector status code (PLC to SCADA); -1=Manual, 0=Off, 1=Auto
.Last_StartTime - Last start time stamp (epoch seconds)
.Last_StopTime - Last stop time stamp (epoch seconds)
.Last_RunTime - Last run duration in seconds
.WallClock_Day - Wall clock day value; required, used for monthly hour rollover
.DateTime_S_DINT - Current epoch time in seconds; required, used for timestamps
.Global_Alm_Reset - Global alarm reset; required

---

## DailyMinMaxAve3

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 2.1. Daily minimum, maximum, and rolling average calculator.
Tracks today's and yesterday's min/max/average values plus month-to-date statistics.
Depends on _LocalDateTime context AOI.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.value - Process value input (GPM); the signal to track
.Reset - Reset all accumulated data
.Reset_dataMTD - Reset month-to-date data only
.Reset_dataZeroDaily - Reset daily accumulator to zero without resetting yesterday's values
.Average - Rolling Average for the last 24 hours (PLC to SCADA)
.Avg_MTD - Month To Date average (PLC to SCADA)
.Avg_Yesterday - Yesterday's average (PLC to SCADA)
.Min - Minimum value for today (PLC to SCADA)
.Min_MTD - Minimum value for month to date (PLC to SCADA)
.Min_Yesterday - Minimum value for yesterday (PLC to SCADA)
.Max - Maximum value for today (PLC to SCADA)
.Max_MTD - Maximum value for month to date (PLC to SCADA)
.Max_Yesterday - Maximum value for yesterday (PLC to SCADA)
.RollingSum24 - Rolling sum for the last 24 hours (PLC to SCADA)

---

## DayOfWeek

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. [No description in source — needs to be written]

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Year - Year input, used to calculate the day of week (required)
.Month - Month input, used to calculate the day of week (required)
.Day - Day input, used to calculate the day of week (required)
.DOW_Output - Calculated day-of-week output code (PLC to SCADA / calling logic)

---

## FaultHandler_Program

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. [No description in source — needs to be written]

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.CurrentFault - Current fault description (InOut, STRING)

---

## _FaultTest_With_Reset

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Fault test for one fault, with reset.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.FaultRecord - Fault record structure (InOut, FAULTRECORD)
.FaultDescription - This is the fault description that will be copied into the fault description output
.CurrentFault - This is the current fault description, output of this module

---

## FLOWIN3_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 0.1. Flow transmitter AOI. Provides hi/lo alarms with hysteresis, channel/range fault alarms,
and full flow totalizer (daily, WTD, MTD, YTD, and lifetime with rollover handling).
Depends on _LocalDateTime and DayOfWeek context AOIs.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Analog_hwai - Flow reading input from transmitter (hardware analog input)
.Hi_scao - High flow alarm setpoint (SCADA to PLC)
.Hi_Rst_Diff_scao - High alarm reset differential; alarm resets at Hi_scao minus this value (SCADA to PLC)
.Lo_scao - Low flow alarm setpoint (SCADA to PLC)
.Lo_Rst_Diff_scao - Low alarm reset differential; alarm resets at Lo_scao plus this value (SCADA to PLC)
.Eng_Hi - Engineering range high value (not used in this AOI)
.Eng_Lo - Engineering range low value (not used in this AOI)
.Disable_Totalizer - Disable flow totalizer accumulation
.Disable_Alarms - Disable all flow alarms
.Hi_Alm_Res - High alarm reset input
.Hi_Alm_Dis - Disable Hi Alarm
.Lo_Alm_Res - Low alarm reset input
.Lo_Alm_Dis - Disable Lo Alarm
.OverRange_hwdi - Over-range fault bit from analog input module (hardware digital input)
.UnderRange_hwdi - Under-range fault bit from analog input module (hardware digital input)
.ChFault_hwdi - Channel fault bit from analog input module (hardware digital input)
.Global_Alm_Reset - Global alarm reset
.Hi_Alm - High Flow Alarm output
.Lo_Alm - Low Flow Alarm output
.OverRange_Alm - OverRange Alarm output
.UnderRange_Alm - Under Range Alarm output
.ChFault_Alm - Channel Fault Alarm output
.Xmtr_Alm - Transmitter Alarm output (any of OverRange, UnderRange, or ChFault active)
.ChFault_Alm_Disable - Disable channel fault alarm
.UnderRange_Alm_Disable - Disable under-range alarm
.OverRange_Alm_Disable - Disable over-range alarm
.Disable_Channel_Alarms - Disable all channel alarms (OverRange, UnderRange, ChFault)
.Total_scai - Today's flow total (PLC to SCADA); resets at midnight
.TotYes_scai - Yesterday's flow total (PLC to SCADA)
.WTD_scai - Week-to-date flow total (PLC to SCADA)
.LstWeek_scai - Last week's flow total (PLC to SCADA)
.MTD_scai - Month-to-date flow total (PLC to SCADA)
.LstMth_scai - Last month's flow total (PLC to SCADA)
.YTD_scai - Year-to-date flow total (PLC to SCADA)
.LstYr_scai - Last year's flow total (PLC to SCADA)
.LIFE_scai - Lifetime Totalizer (PLC to SCADA); uses rollover counter to prevent float precision loss
.End_Of_Week - Day number that marks the end of the week for WTD rollover (default = 1, Sunday)
.Lo_Alm_Sec_Delay_SP - Low alarm activation delay (seconds); default 10
.Hi_Alm_Sec_Delay_SP - High alarm activation delay (seconds); default 10
.Lo_Cutoff_scai - Lowest recordable analog input value; readings below this are treated as zero flow
.Negative_Cutoff_scai - Below this value the analog device appears to have lost power
.Hi_Alm_Enable - Process enable of Hi Alarm (set false to suppress independently of Disable)
.Lo_Alm_Enable - Process enable of Lo Alarm (set false to suppress independently of Disable)
.MRC - Monthly Rollover Count; number of times MTD register has rolled over
.MTD_intm - Intermediate MTD accumulator before rollover correction (read-only)
.YRC - Yearly Rollover Count; number of times YTD register has rolled over
.YTD_intm - Intermediate YTD accumulator before rollover correction (read-only)
.LRC - Lifetime Rollover Count; number of times LIFE register has rolled over
.LIFE_intm - Intermediate LIFE accumulator before rollover correction (read-only)

---

## FLOWVLV_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.4. On/off valve control AOI. Use for on/off valves only — not proportional/analog valves.
Provides dual-coil actuate/de-actuate outputs, fail-to-actuate and fail-to-de-actuate alarms, runtime hour tracking,
and standard AutoCall interlock inputs.

AUTO_STATUS_scai values: 1=Auto, 2=not Auto from SCADA, 3=not Auto hardware, 4=neither, 5=Manual hardware, 99=error
State values: 0=Open, 1=Closed, 2=Traveling, 99=I/O error

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.AUTO_hwdi - HOA selector switch auto position (hardware digital input); required
.MAN_hwdi - HOA selector switch manual/hand position (hardware digital input); required
.Disable_Alarms - Disable all alarms
.AUTO_PB_scdo - SCADA Auto mode pushbutton command (SCADA to PLC)
.AUTO_scdi - SCADA Auto mode status feedback (PLC to SCADA)
.MAN_scdi - SCADA Manual mode status feedback (PLC to SCADA)
.START_scdo - SCADA actuate/open command (SCADA to PLC); momentary bit unlatched at end of scan
.STOP_scdo - SCADA de-actuate/close command (SCADA to PLC); momentary bit unlatched at end of scan
.ENABLE_PB_scdo - SCADA enable pushbutton command (SCADA to PLC)
.DISABLE_PB_scdo - SCADA disable pushbutton command (SCADA to PLC)
.HOURS_scai - Actuated-position runtime hours accumulator (PLC to SCADA)
.AutoCall_scdi - AutoCall demand bit; when true PLC logic requests valve to actuate (SCADA to PLC)
.INTRLK_scdi - Standard enable interlock; energize (1) to permit AutoCall actuate output
.AutoCall_INTRLK_scdi - Inverse enable interlock; energize (1) to disable AutoCall actuate output
.ACTUATE_hwdo - Actuate coil output to valve (hardware digital output); required
.DEACTUATE_hwdo - De-actuate coil output to valve (hardware digital output); required
.START_hwdo - Start hardware digital output (auxiliary, not typically used)
.STOP_hwdo - Stop hardware digital output (auxiliary, not typically used)
.ENABLE_hwdo - Enable hardware digital output (auxiliary, not typically used)
.RESET_hwdo - Reset hardware digital output (auxiliary, not typically used)
.Actuated_hwdi - Actuated (open) position feedback from valve limit switch (hardware digital input); required
.FAIL_ACT_alm - Fail to actuate alarm output
.FAIL_alm_res - Fail alarm reset input
.FAIL_ACT_alm_dis - Disable fail-to-actuate alarm
.Fail_Alm_Ack_In - Fail alarm acknowledge input (from alarm server)
.FAIL_ACT_alm_ack - Fail-to-actuate alarm acknowledge input
.Deactuated_hwdi - De-actuated (closed) position feedback from valve limit switch (hardware digital input); required
.FAIL_DEACT_alm - Fail to de-actuate alarm output
.FAIL_DEACT_alm_dis - Disable fail-to-de-actuate alarm
.FAIL_DEACT_alm_ack - Fail-to-de-actuate alarm acknowledge input
.Ack_All - Acknowledge all alarms
.Global_Alm_Reset - Global alarm reset
.DEACTUATE_Dis_scdo - Disable de-actuate output; not typically used (SCADA to PLC)
.RESETTMR_scdo - Reset runtime timer command (SCADA to PLC)
.AUTO_STATUS_scai - Auto mode status code (PLC to SCADA)
.State - Valve position state (PLC to SCADA); 0=Open, 1=Closed, 2=Traveling, 99=I/O error

---

## INTERLOCK_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Interlock visualization AOI. Provides HMI animation of interlock states using
extended tag properties. Each of the 32 Interlocks bits should have its description set to the
interlock name; those descriptions appear in the HMI via the extended tag mechanism.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Interlocks - DINT with 32 interlock bits (bits 0-31); set bit description in Studio 5000 for each interlock used
.Visibility - DINT controlling which interlock bits are visible in HMI (0=invisible, 1=visible per bit); default all visible
.OutputState - Overall output state; true when any visible interlock bit is set

---

## L_ModuleSts

**Source:** Rockwell Automation
**Last updated:** 2026-09-03

Revision 4.0 (RevisionExtension ".00 Release"). Logix - Module Status. Checks the I/O connection status
of a given module (Ref_Module); if the status is not "running", Sts_IOFault is raised. For use with
Studio 5000 Logix Designer and Logix controller firmware v24 and later. Part of Rockwell's Process Library.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Ref_Module - Module (from I/O Configuration tree) whose status is sought (InOut)
.Inp_Sim - 1=Use Simulated Module Status, 0=Report Actual Module Status
.Set_SimFault - When in Simulation: 1=Module Faulted, 0=Module OK
.Sts_IOFault - 1=Module I/O communication fault (not in Running state)

---

## LEVELIN3_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.1. Level transmitter AOI. Provides four-level alarms (HiHi/Hi/Lo/LoLo) with hysteresis,
channel/range fault alarms, up to five pump on/off level setpoints, percent and gallon level outputs,
and tank feet/inches conversion.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.ANALOG_hwai - Level transmitter analog input in inches (hardware analog input); required
.Percent_scai - Level as percent of range (PLC to SCADA)
.Gallon_scai - Level in gallons calculated from tank geometry (PLC to SCADA)
.Pump1On_scao - Pump 1 lead-on level setpoint in inches (SCADA to PLC)
.Pump1Off_scao - Pump 1 lead-off level setpoint in inches (SCADA to PLC)
.Pump2On_scao - Pump 2 lag-on level setpoint in inches (SCADA to PLC)
.Pump2Off_scao - Pump 2 lag-off level setpoint in inches (SCADA to PLC)
.Pump3On_scao - Pump 3 lag-on level setpoint in inches (SCADA to PLC)
.Pump3Off_scao - Pump 3 lag-off level setpoint in inches (SCADA to PLC)
.Pump4On_scao - Pump 4 lag-on level setpoint in inches (SCADA to PLC)
.Pump4Off_scao - Pump 4 lag-off level setpoint in inches (SCADA to PLC)
.Pump5On_scao - Pump 5 lag-on level setpoint in inches (SCADA to PLC)
.Pump5Off_scao - Pump 5 lag-off level setpoint in inches (SCADA to PLC)
.HiHi_scao - HiHi alarm setpoint in inches (SCADA to PLC)
.HiHi_Rst_Diff_scao - HiHi alarm reset differential; alarm resets at HiHi_scao minus this value (SCADA to PLC)
.Hi_scao - Hi alarm setpoint in inches (SCADA to PLC)
.Hi_Rst_Diff_scao - Hi alarm reset differential; alarm resets at Hi_scao minus this value (SCADA to PLC)
.Lo_scao - Lo alarm setpoint in inches (SCADA to PLC)
.Lo_Rst_Diff_scao - Lo alarm reset differential; alarm resets at Lo_scao plus this value (SCADA to PLC)
.LoLo_scao - LoLo alarm setpoint in inches (SCADA to PLC)
.LoLo_Rst_Diff_scao - LoLo alarm reset differential; alarm resets at LoLo_scao plus this value (SCADA to PLC)
.XmtrOffset_scao - Transmitter zero offset correction in inches (SCADA to PLC)
.WaterElevation_scai - Calculated water surface elevation in inches (PLC to SCADA; not wired by AOI)
.ENG_Hi - Engineering range high value in inches; used for percent calculation
.ENG_Lo - Engineering range low value in inches; used for percent calculation
.CNT_Hi - Count-based high engineering value (placeholder)
.CNT_Lo - Count-based low engineering value (placeholder)
.LVL_Alm_RstPerc - Level alarm reset percentage; REMOVED FROM AOI (legacy tag, not used)
.Modes_scai - Mode status code (placeholder, not written by AOI)
.OverRange_hwdi - Over-range fault bit from analog input module (hardware digital input); required
.UnderRange_hwdi - Under-range fault bit from analog input module (hardware digital input); required
.ChFault_hwdi - Channel fault bit from analog input module (hardware digital input); required
.Online_scdo - Online command from SCADA (SCADA to PLC)
.Disable_Channel_Alarms - Disable all channel alarms (OverRange, UnderRange, ChFault)
.HiHi_Alm_Ack - HiHi alarm acknowledged status (output)
.HiHi_Alm_Res - HiHi alarm reset input
.HiHi_Alm_Dis - Disable HiHi alarm
.Hi_Alm_Ack - Hi alarm acknowledged status (output)
.Hi_Alm_Res - Hi alarm reset input
.Hi_Alm_Dis - Disable Hi alarm
.Lo_Alm_Ack - Lo alarm acknowledged status (output)
.Lo_Alm_Res - Lo alarm reset input
.Lo_Alm_Dis - Disable Lo alarm
.LoLo_Alm_Ack - LoLo alarm acknowledged status (output)
.LoLo_Alm_Res - LoLo alarm reset input
.LoLo_Alm_Dis - Disable LoLo alarm
.Ack_All - Acknowledge all alarms
.Global_Alm_Reset - Global alarm reset; required
.OverRange_Ack - Over-range alarm acknowledged status (output)
.UnderRange_Ack - Under-range alarm acknowledged status (output)
.ChFault_Ack - Channel fault alarm acknowledged status (output)
.HiHi_Alm - HiHi Alarm output
.Hi_Alm - Hi Alarm output
.Lo_Alm - Lo Alarm output
.LoLo_Alm - LoLo Alarm output
.OverRange_Alm - OverRange Alarm output
.UnderRange_Alm - UnderRange Alarm output
.ChFault_Alm - Channel Fault Alarm output
.Xmtr_Alm - Transmitter Alarm output (any channel fault active)
.HiHi_Alm_Ack_In - HiHi alarm acknowledge input (from alarm server)
.Hi_Alm_Ack_In - Hi alarm acknowledge input (from alarm server)
.Lo_Alm_Ack_In - Lo alarm acknowledge input (from alarm server)
.LoLo_Alm_Ack_In - LoLo alarm acknowledge input (from alarm server)
.ChFault_Ack_In - Channel fault alarm acknowledge input (from alarm server)
.UnderRange_Ack_In - Under-range alarm acknowledge input (from alarm server)
.OverRange_Ack_In - Over-range alarm acknowledge input (from alarm server)
.UnACK_Alm - Unacknowledged alarm present (output)
.State - Level state output (placeholder)
.HiHiAlm_State - HiHi alarm state code (output)
.HiAlm_State - Hi alarm state code (output)
.LoAlm_State - Lo alarm state code (output)
.LoLoAlm_State - LoLo alarm state code (output)
.ChFault_Alm_State - Channel fault alarm state code (output)
.OverRange_Alm_State - Over-range alarm state code (output)
.UnderRange_Alm_State - Under-range alarm state code (output)
.HiHi_Alm_TMR_ACC - HiHi alarm debounce timer accumulated value (output)
.HiHi_Alm_TMR_PRE - HiHi alarm debounce timer preset (seconds); default 5
.Hi_Alm_TMR_ACC - Hi alarm debounce timer accumulated value (output)
.Hi_Alm_TMR_PRE - Hi alarm debounce timer preset (seconds); default 5
.Lo_Alm_TMR_ACC - Lo alarm debounce timer accumulated value (output)
.Lo_Alm_TMR_PRE - Lo alarm debounce timer preset (seconds); default 5
.LoLo_Alm_TMR_ACC - LoLo alarm debounce timer accumulated value (output)
.LoLo_Alm_TMR_PRE - LoLo alarm debounce timer preset (seconds); default 5
.Disable_lvl_alarms - Disables HiHi, Hi, Lo, and LoLo alarms simultaneously
.Tank_Feet_WholeNumber - Tank level in whole feet (output; derived from ANALOG_hwai / 12)
.Tank_Inches_Remainder - Tank level inches remainder after feet conversion (output)
.Gross_Gallons - Gross tank capacity in gallons (used with Net_Gallons for level-to-volume calculation)
.Net_Gallons - Net usable tank capacity in gallons (used for Gallon_scai calculation)

---

## _LocalDateTime

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. [No description in source — needs to be written]

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Year - Current year (output)
.Month - Current month (output)
.Day - Current day (output)
.Hour - Current hour (output)
.Minute - Current minute (output)
.Second - Current second (output)
.MicroSecond - Current microsecond (output)

---

## MODVLV

**Source:** Casne (confirmed by Doug, 2026-09-03) — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

UDT — Modulating Valve (MODVLV). User-Defined Data Type for a PID-controlled proportional valve.
Bundles all setpoints, PID controller, mode bits, position I/O, and fault alarms into one tag structure.
Source file: MODVLV_DataType.L5X

.MANPOS_scao - Manual Position Setpoint (SCADA to PLC); operator-entered position when in manual mode
.SETPOINT_scao - Loop setpoint scaled in engineering units (SCADA to PLC)
.LGAIN - Loop controller proportional gain
.LERR - Loop error (PV minus SP)
.CVMIN - Control Variable minimum clamp level; lower output limit
.CVMAX - Control Variable maximum clamp level; upper output limit
.DBAND - Dead band; error within this range produces no corrective output
.EUMAX - Engineering units maximum; high end of PV range
.EUMIN - Engineering units minimum; low end of PV range
.LD - Loop derivative gain component
.LI - Loop integral gain component
.CV - PID Control Variable output; current computed output value
.PV - Process variable; current measured value fed to PID
.FAILCLS_alm_dis - Fail-to-close alarm disable
.POS_scai - Position Status; current valve position feedback (PLC to SCADA)
.POS_hwao - Position Output; analog position command sent to valve actuator (hardware analog output)
.MODE - Operating mode
.LBIAS - Bias component of loop controller output
.CLOSE_hwdi - Closed Status from valve limit switches (hardware digital input)
.OPEN_hwdi - Open Status from valve limit switches (hardware digital input)
.AUTO_PB_scdo - SCADA Auto Mode Command (SCADA to PLC)
.MAN_PB_scdo - SCADA Manual Mode Command (SCADA to PLC)
.AUTO_scdi - SCADA Auto Mode Status (PLC to SCADA)
.MAN_scdi - SCADA Manual Mode Status (PLC to SCADA)
.Offline_scdo - Offline bit used for auto-tune (ATune) mode
.FAILOPN_alm_res - Fail-to-open alarm reset
.FAILCLS_alm_res - Fail-to-close alarm reset
.FAILOPN_alm_dis - Fail-to-open alarm disable
.CHFault_alm_ack - Analog Output channel fault alarm acknowledge
.OpenWire_alm_ack - Analog Output open wire alarm acknowledge
.INTRLK_scdi - Interlock signal from remote device (PLC to SCADA)
.AVAIL_scdi - Available to operate in Auto (PLC to SCADA)
.FAILOPN_alm - Valve Failed to Open alarm
.FAILCLS_alm - Valve Failed to Close alarm
.CHFault_alm - Analog Output Channel Fault alarm
.OpenWire_alm - Analog Output Channel Open Wire alarm
.LPID - PID loop active bit
.LPIDc - PID loop cascade bit
.PID_Auto - PID auto bit; true when PID controller is in automatic mode
.AutoToManualOS - One-shot bit set on transition from Auto to Manual mode
.ManualToAutoOS - One-shot bit set on transition from Manual to Auto mode
.DLYTMR - PID delay timer (TIMER structured sub-object)
.PID - PID control block for valve position (PID structured sub-object)
.FTO_TMR - Fail-to-open alarm timer (TIMER structured sub-object)
.FTC_TMR - Fail-to-close alarm timer (TIMER structured sub-object)

---

## PROCESSOR_STATUS

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Processor Status.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.key_run - Key in run position
.key_prog - Key in program position
.key_remote - Key in remote position
.Test_Mode - Test mode status (output)
.edits_enabled - Online edits enabled status (output)
.edits_disabled - Online edits disabled status (output)
.forces_present - I/O forces present status (output)
.forces_enabled - I/O forces enabled status (output)
.forces_present_and_enabled - I/O forces present and enabled status (output)
.PLC_Device_Name - PLC device name string (InOut, SINT[33])
.first_scan - First scan bit (output)
.PLC_STATUS - PLC status array (InOut, DINT[7])

---

## Prog_Scan_Times

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Program Scan Times.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Program_time - Current program scan time (output)
.max_Scantime - Maximum recorded program scan time (output)

---

## RollingSum

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 0.0. Rolling sum and average calculator over a configurable time window.
Accumulates a process value over the last N minutes and outputs the sum and average.
Depends on _LocalDateTime context AOI. Created by Doug Sparks, 4/9/26.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.value - Process value input (GPM); the signal to accumulate
.Reset - Reset the rolling accumulator
.NumMinutes - Rolling window length in minutes (DINT); default 1440 (24 hours)
.RollingAve - Rolling average over the window period (output, gallons)
.RollingSum - Rolling sum over the window period (output, gallons)

---

## STATUS

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Minor faults.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.LowBattery - Low battery status (output)
.Periodic_task - Periodic task status (output)
.rS232_error - RS232 communication error status (output)

---

## TimeSec

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. [No description in source — needs to be written]

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.TimeInMicroSeconds - Time value in microseconds (InOut, LINT)
.TimeInSeconds - Time value in seconds (InOut, LINT)

---

## VARSPD2_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 2.1. Variable-speed drive (VFD) AOI. Extends CONSPD4_AOI with analog speed command/feedback,
drive fault, channel fault, open-wire alarms, hi/lo current alarms, and PPM/Constant speed calculation modes.

Parameters are stored alphabetically in the L5X file.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.Ack_All - Acknowledge all alarms
.ALRM_ack - General alarm acknowledge input
.ALRM_Ack_In - General alarm acknowledge input (from alarm server)
.ALRM_dis - Disable general alarm
.ALRM_res - General alarm reset input
.ALRM_hwdi - General alarm hardware digital input (optional external alarm source)
.ALRM_Invert - Invert the ALRM_hwdi signal polarity
.AUTO_hwdi - HOA selector switch is in the auto position (hardware digital input); required
.AUTO_PB_scdo - SCADA Auto mode pushbutton command (SCADA to PLC)
.AutoCall_scdi - AutoCall demand bit; when true PLC logic requests drive to run
.AutoCall_INTRLK_scdi - De-energize to run interlock; must be false for AutoCall to run drive
.AVAIL_scdi - Drive available status input; indicates drive is ready to run
.CBAux_alm_ack - CB auxiliary alarm acknowledge input
.CBAux_Alm_dis - Disable CB auxiliary alarm
.CBAux_Alm_res - CB auxiliary alarm reset input
.CBAux_hwdi - CBAux Hardware Input; circuit breaker auxiliary contact
.CBAux_Invert - Invert the CBAux_hwdi signal polarity
.CBAux_Alm_Ack_In - CB auxiliary alarm acknowledge input (from alarm server)
.ChFault_alm_ack - Channel fault alarm acknowledge input
.ChFault_alm_dis - Disable channel fault alarm
.ChFault_alm_res - Channel fault alarm reset input
.ChFault_Alm_Ack_In - Channel fault alarm acknowledge input (from alarm server)
.ChFault_hwdi - Channel fault bit from analog input module
.Current_HiAlm_Ack_In - Current high alarm acknowledge input (from alarm server)
.Current_LoAlm_Ack_In - Current low alarm acknowledge input (from alarm server)
.Constant_scao - Constant speed multiplier for DAF influent flow rate speed calculation (SCADA to PLC)
.Constant_EN_scdo - Enable Constant calculation mode for pump speed control (SCADA to PLC)
.CURRENT_HiAlm_ack - Current high alarm acknowledge input
.CURRENT_HiAlm_dis - Disable current high alarm
.CURRENT_HiAlm_res - Current high alarm reset input
.CURRENT_LoAlm_ack - Current low alarm acknowledge input
.CURRENT_LoAlm_dis - Disable current low alarm
.CURRENT_LoAlm_res - Current low alarm reset input
.CURRENT_HiAlm_SP - VFD high current alarm setpoint (amperes)
.Current_hwai - VFD Current Feedback (hardware analog input, amperes)
.CURRENT_LoAlm_SP - VFD low current alarm setpoint (amperes)
.Disable_Alarms - Disable all alarms
.DriveFault_Alm_Ack_In - Drive fault alarm acknowledge input (from alarm server)
.DriveFault_ack - Drive fault alarm acknowledge input
.DriveFault_alm_dis - Disable drive fault alarm
.DriveFault_alm_res - Drive fault alarm reset input
.DriveFault_hwdi - Drive Fault Hardware Input (hardware digital input)
.DriveFault_Invert - Invert the DriveFault_hwdi signal polarity
.Fail_Alm_Ack_In - Fail-to-run alarm acknowledge input (from alarm server)
.FAIL_alm_ack - Fail-to-run alarm acknowledge input
.FAIL_alm_dis - Disable fail-to-run alarm
.FAIL_alm_res - Fail-to-run alarm reset input
.Global_Alm_Reset - Global alarm reset; required
.MAN_hwdi - HOA selector switch is in the manual/hand position (hardware digital input); required
.INTRLK_scdi - Energize to run interlock; must be true for AutoCall to run drive
.MAN_PB_scdo - SCADA Manual mode pushbutton command (SCADA to PLC)
.ManSpeed_SP - Manual Speed Setpoint in Hz (0-60 Hz range); used when in manual mode
.OpenWire_alm_ack - Open-wire alarm acknowledge input
.OpenWire_alm_dis - Disable open-wire alarm
.OpenWire_alm_res - Open-wire alarm reset input
.OpenWire_Alm_Ack_In - Open-wire alarm acknowledge input (from alarm server)
.OpenWire_hwdi - Open-wire fault bit from analog output module
.PID_Auto - PID Control in Auto mode; informational bit used outside AOI logic
.PPM_EN_scdo - Enable PPM calculation mode for pump speed control (SCADA to PLC)
.PPM_scao - Parts-per-million setpoint for DAF influent flow rate speed calculation (SCADA to PLC)
.PV - Process Variable; external PV used for speed calculations (not wired internally)
.Prority_scai - Priority code placeholder (not written by AOI)
.RESET_scdo - Reset command (SCADA to PLC)
.RESETTMR_scdo - Reset runtime timer command (SCADA to PLC)
.Running_ONS - Running one-shot latch bit (external use)
.Running_hwdi - Motor/drive running feedback (hardware digital input); required
.Setpoint_scao - Speed command setpoint in Hz written by SCADA (SCADA to PLC)
.SpeedFB_hwai - Speed feedback from VFD in Hz (hardware analog input); required
.START_scdo - SCADA Start command (SCADA to PLC); momentary, unlatched at end of scan
.Status_scai - Status code placeholder (not written by AOI)
.STOP_scdo - SCADA Stop command (SCADA to PLC)
.Stuck_On_Alm_Time_Setpoint - How long drive should run before triggering stuck-on alarm (minutes); default 20
.Stuck_On_Alm_dis - Disable stuck-on alarm
.Stuck_On_Alm_res - Stuck-on alarm reset input
.WallClock_Day - Wall clock day value; required, used for monthly hour rollover
.ALRM - General alarm output bit
.AUTO_scdi - SCADA Auto mode status (PLC to SCADA)
.CBAux_alm - CB auxiliary alarm output
.ChFault_alm - Channel fault alarm output
.CURRENT_HiAlm - Current high alarm output
.CURRENT_LoAlm - Current low alarm output
.DriveFault_alm - Drive fault alarm output
.FAIL_alm - Fail-to-run alarm output; PLC called drive to run, motor failed to provide running feedback
.FaultCode_scai - Fault code output (PLC to SCADA)
.HOA_STATUS_scai - HOA selector status code (PLC to SCADA); -1=Manual, 0=Off, 1=Auto
.HOURS_scai - Total lifetime runtime hours (PLC to SCADA)
.MAN_scdi - SCADA Manual mode status (PLC to SCADA)
.MONTH_HOURS_scai - Current month runtime hours (PLC to SCADA)
.MOTOR_STATUS_scai - Motor status code (PLC to SCADA); 0=stopped, 1=running, 2=fault
.OpenWire_alm - Open-wire alarm output
.PREV_MONTH_HOURS_scai - Previous month runtime hours (PLC to SCADA)
.RESET_hwdo - Reset hardware digital output
.RUN_hwdo - Run command output (hardware digital output); required
.Speed_hwao - Speed command output to VFD in Hz (hardware analog output); required
.START_hwdo - Start hardware digital output (auxiliary)
.State - Drive/motor state output
.STOP_hwdo - Stop hardware digital output (auxiliary)
.Stuck_On_Alm - Pump Stuck on / Runtime Alarm output
.UnACK_Alm - Unacknowledged alarm present (output)
.AUTO_STATUS_scai - Auto mode status code (PLC to SCADA)

---

## VARSPD_PIDE_AOI

**Source:** Casne — Blue Sky O2 program (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X
**Last updated:** 2026-09-03

Revision 1.0. Handles switching between manual and auto operation for a variable-speed PIDE control loop,
ensuring bumpless transfer between auto/manual/auto modes. In Manual, the operator commands speed directly
from SCADA; in Auto, PIDE adjusts speed to maintain the ProcessVariable at the operator-entered setpoint.
Uses the paired VARSPD2_AOI instance's PID_Auto bit to select mode, applies operator CVMIN_scao/CVMAX_scao
limits to the PIDE output, maps ProcessVariable to PV and ControlVariable to CV, and preserves smooth
transitions between operating modes. Created 8/27/26.

.EnableIn - Enable Input - System Defined Parameter
.EnableOut - Enable Output - System Defined Parameter
.DRIVE_Name - VFD Drive Name (InOut, VARSPD2_AOI instance)
.PIDE_Name - PIDE name (InOut, PID_ENHANCED instance)
.CVMAX_scao - CVMAX SCADA to PLC
.CVMIN_scao - CVMIN SCADA to PLC
.ProcessVariable - Process Variable to be mapped into the PIDE.PV
.ControlVariable - PIDE.CV will be mapped into the Control Variable
