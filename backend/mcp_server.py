from mcp.server.fastmcp import FastMCP

from tools.book_appointment import book_appointment
from tools.check_availability import check_doctor_availability
from tools.doctor_summary import doctor_summary_report

mcp = FastMCP("DoctorAssistant")


@mcp.tool()
def check_doctor_availability_tool(doctor_name: str, date: str, time_range: str = "all") -> str:
    # expose availability as tool
    return check_doctor_availability(doctor_name, date, time_range)


@mcp.tool()
def book_appointment_tool(
    doctor_name: str,
    patient_name: str,
    date: str,
    time: str,
    reason: str = "General Consultation",
    patient_email: str = "",
) -> str:
    # expose booking as tool
    return book_appointment(doctor_name, patient_name, date, time, reason, patient_email)


@mcp.tool()
def doctor_summary_report_tool(date: str) -> str:
    # expose summary as tool
    return doctor_summary_report(date)


if __name__ == "__main__":
    # start mcp tool server
    mcp.run()
