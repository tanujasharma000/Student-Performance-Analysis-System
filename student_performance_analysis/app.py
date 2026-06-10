import matplotlib 
matplotlib.use('Agg')           
import matplotlib.pyplot as plt
from flask import Flask, render_template, redirect, url_for, request, session, Response
import pandas as pd
import os
import smtplib
from email.message import EmailMessage
from email_sender import send_email
import io

app= Flask( __name__, static_folder='static', static_url_path='/static')
app.secret_key=""

@app.route('/')
def home():
    return render_template("index.html")

UPLOAD_FOLDER="uploads"
app.config["UPLOAD_FOLDER"]=UPLOAD_FOLDER

@app.route("/upload", methods=["GET", "POST"])
def upload():
    report = None

    if request.method == "POST":
        file = request.files["file"]

        if file:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            df = pd.read_csv(filepath)

            # -------------------------------
            # ✅ AUTO-DETECT SUBJECT COLUMNS
            # -------------------------------
            exclude_cols = ["name", "email", "department", "semester", "attendance"]
            subjects = [col for col in df.columns if col not in exclude_cols]

            # ensure numeric conversion (safe handling)
            df[subjects] = df[subjects].apply(pd.to_numeric, errors="coerce")

            # -------------------------------
            # AVERAGE CALCULATION
            # -------------------------------
            df["average"] = df[subjects].mean(axis=1)

            # -------------------------------
            # BASIC STATS
            # -------------------------------
            total_students = len(df)
            overall_average = round(df["average"].mean(), 2)
            highest_marks = round(df["average"].max(), 2)
            lowest_marks = round(df["average"].min(), 2)

            # top student
            top_student = df.loc[df["average"].idxmax()]["name"]

            # -------------------------------
            # WEAK STUDENTS
            # -------------------------------
            weak_df = df[df["average"] < 40]
            weak_students = weak_df.to_dict(orient="records")
            weak_count = len(weak_df)

            # pass percentage
            pass_percentage = round(((total_students - weak_count) / total_students) * 100, 2)

            # -------------------------------
            # SUBJECT AVERAGES
            # -------------------------------
            subject_avg = df[subjects].mean().round(2).to_dict()

            # -------------------------------
            # ATTENDANCE ANALYSIS (SAFE)
            # -------------------------------
            if "attendance" in df.columns:
                avg_attendance = round(df["attendance"].mean(), 2)
                low_attendance_df = df[df["attendance"] < 75]
            else:
                avg_attendance = 0
                low_attendance_df = pd.DataFrame()

            low_attendance_count = len(low_attendance_df)

            # -------------------------------
            # PERFORMANCE CATEGORIES
            # -------------------------------
            excellent = len(df[df["average"] >= 80])
            good = len(df[(df["average"] >= 60) & (df["average"] < 80)])
            average = len(df[(df["average"] >= 40) & (df["average"] < 60)])
            weak = len(df[df["average"] < 40])

            # -------------------------------
            # REPORT DICTIONARY
            # -------------------------------
            report = {
                "total_students": total_students,
                "overall_average": overall_average,
                "highest_marks": highest_marks,
                "lowest_marks": lowest_marks,
                "top_student": top_student,
                "weak_students": weak_students,
                "weak_count": weak_count,
                "pass_percentage": pass_percentage,
                "subject_avg": subject_avg,
                "avg_attendance": avg_attendance,
                "low_attendance_count": low_attendance_count,
                "excellent": excellent,
                "good": good,
                "average": average,
                "weak": weak
            }

            # store in session
            session["report"] = report
            session["data"] = df.to_dict(orient="records")
            session["weak_students"] = weak_students

    return render_template("upload.html", report=report)

from flask import send_file


@app.route("/download_report")
def download_report():
    report = session.get("report")

    # safety check (IMPORTANT)
    if not report:
        return "No report found. Please upload a file first."

    filename = os.path.join(os.getcwd(), "report.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("STUDENT PERFORMANCE REPORT\n\n")
        f.write(f"Total Students: {report.get('total_students', 0)}\n")
        f.write(f"Overall Average: {report.get('overall_average', 0)}\n")
        f.write(f"Highest Marks: {report.get('highest_marks', 0)}\n")
        f.write(f"Lowest Marks: {report.get('lowest_marks', 0)}\n")
        f.write(f"Top Student: {report.get('top_student', 'N/A')}\n")
        f.write(f"Weak Students Count: {report.get('weak_count', 0)}\n")
        f.write(f"Pass Percentage: {report.get('pass_percentage', 0)}\n")
        f.write(f"Excellent Students: {report.get('excellent', 0)}\n")
        f.write(f"Good Students: {report.get('good', 0)}\n")
        f.write(f"Average Students: {report.get('average', 0)}\n")
        f.write(f"Weak Students: {report.get('weak', 0)}\n")
        f.write(f"Low Attendance Count: {report.get('low_attendance_count', 0)}\n")

    return send_file(filename, as_attachment=True)
# --------------------- DYNAMIC GRAPHS ---------------------
from flask import Response
import pandas as pd
import matplotlib.pyplot as plt
import io

# -------------------------------
# 1. SUBJECT AVERAGE BAR GRAPH
# -------------------------------
@app.route("/subject_avg_plot.png")
def subject_avg_plot():
    data = session.get("data")
    if not data:
        return ""

    df = pd.DataFrame(data)

    # dynamic subjects
    exclude_cols = ["name", "email", "department", "semester", "attendance"]
    subjects = [col for col in df.columns if col not in exclude_cols]

    df[subjects] = df[subjects].apply(pd.to_numeric, errors="coerce")
    subject_avg = df[subjects].mean()

    fig, ax = plt.subplots(figsize=(6, 4))
    subject_avg.plot(kind="bar", ax=ax)
    ax.set_title("Subject Average Marks")
    ax.set_ylabel("Marks")
    plt.tight_layout()

    img = io.BytesIO()
    fig.savefig(img, format="png")
    img.seek(0)
    plt.close(fig)

    return Response(img.getvalue(), mimetype="image/png")


# -------------------------------
# 2. PASS / FAIL PIE CHART
# -------------------------------
@app.route("/pass_fail_plot.png")
def pass_fail_plot():
    data = session.get("data")
    if not data:
        return ""

    df = pd.DataFrame(data)

    pass_count = len(df[df["average"] >= 40])
    fail_count = len(df[df["average"] < 40])

    fig, ax = plt.subplots()
    ax.pie(
        [pass_count, fail_count],
        labels=["Pass", "Fail"],
        autopct="%1.1f%%"
    )
    ax.set_title("Pass vs Fail")

    img = io.BytesIO()
    fig.savefig(img, format="png")
    img.seek(0)
    plt.close(fig)

    return Response(img.getvalue(), mimetype="image/png")


# -------------------------------
# 3. PERFORMANCE CATEGORY BAR GRAPH
# -------------------------------
@app.route("/performance_plot.png")
def performance_plot():
    data = session.get("data")
    if not data:
        return ""

    df = pd.DataFrame(data)

    categories = {
        "Excellent": len(df[df["average"] >= 80]),
        "Good": len(df[(df["average"] >= 60) & (df["average"] < 80)]),
        "Average": len(df[(df["average"] >= 40) & (df["average"] < 60)]),
        "Weak": len(df[df["average"] < 40])
    }

    fig, ax = plt.subplots()
    ax.bar(categories.keys(), categories.values())
    ax.set_title("Performance Categories")
    ax.set_ylabel("Number of Students")

    img = io.BytesIO()
    fig.savefig(img, format="png")
    img.seek(0)
    plt.close(fig)

    return Response(img.getvalue(), mimetype="image/png")


# -------------------------------
# 4. ATTENDANCE HISTOGRAM
# -------------------------------
@app.route("/attendance_plot.png")
def attendance_plot():
    data = session.get("data")
    if not data:
        return ""

    df = pd.DataFrame(data)

    if "attendance" not in df.columns:
        return ""

    df["attendance"] = pd.to_numeric(df["attendance"], errors="coerce")

    fig, ax = plt.subplots()
    df["attendance"].plot(kind="hist", ax=ax, bins=10)
    ax.set_title("Attendance Distribution")
    ax.set_xlabel("Attendance %")
    ax.set_ylabel("Number of Students")

    img = io.BytesIO()
    fig.savefig(img, format="png")
    img.seek(0)
    plt.close(fig)

    return Response(img.getvalue(), mimetype="image/png")

# --------------------- DASHBOARD ROUTE ---------------------

@app.route("/dashboard")
def dashboard():
    data = session.get("data")

    if not data:
        return render_template("dashboard.html", no_data=True, students=[])

    df = pd.DataFrame(data)
    students = df.to_dict(orient="records")

    return render_template(
        "dashboard.html",
        students=students,
        no_data=False
    )
# --------------------- SEND EMAIL ---------------------
@app.route("/about")
def about():
    return render_template("about.html") 

@app.route("/send_email")
def send_email_route():
    weak_students = session.get("weak_students", [])

    if not weak_students:
        return redirect(url_for("dashboard"))

    for student in weak_students:
        email = student.get("email")
        name = student.get("name", "Student")
        marks = student.get("average", 0)

        # safety check
        if email:
            send_email(email, name, marks)

    return redirect(url_for("dashboard"))
if __name__=="__main__":
    app.run(debug=True)
