import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("library.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Authors (
            AuthorID INTEGER PRIMARY KEY,
            AuthorName TEXT,
            Nationality TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Books (
            BookID INTEGER PRIMARY KEY,
            Title TEXT,
            AuthorID INTEGER,
            AvailableCopies INTEGER,
            FOREIGN KEY(AuthorID) REFERENCES Authors(AuthorID)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Members (
            MemberID INTEGER PRIMARY KEY,
            FullName TEXT,
            Email TEXT UNIQUE
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Borrow (
            BorrowID INTEGER PRIMARY KEY,
            BookID INTEGER,
            MemberID INTEGER,
            IssueDate DATE,
            DueDate DATE,
            ReturnDate DATE,
            FineAmount REAL DEFAULT 0,
            FOREIGN KEY(BookID) REFERENCES Books(BookID),
            FOREIGN KEY(MemberID) REFERENCES Members(MemberID)
        )
        """
    )

    conn.commit()
    return conn


# --- APP UI ---
st.set_page_config(page_title="Student Library System", layout="wide")
st.markdown(
    """
    <div style='display:flex; align-items:center; gap:10px;'>
      <div style='font-size:34px;'>📚</div>
      <div><h1 style='margin:0; font-size:28px;'>Student Library Management</h1></div>
    </div>
    """,
    unsafe_allow_html=True,
)

menu = ["Dashboard", "Manage Books", "Issue/Return", "Members & Fines"]
choice = st.sidebar.selectbox("Navigation", menu)

conn = init_db()

if choice == "Dashboard":
    st.subheader("Library Overview")
    query = """
    SELECT b.Title, a.AuthorName, b.AvailableCopies
    FROM Books b
    JOIN Authors a ON b.AuthorID = a.AuthorID
    """
    df = pd.read_sql(query, conn)
    st.dataframe(df, use_container_width=True)

elif choice == "Manage Books":
    st.subheader("Add New Content")
    col1, col2 = st.columns(2)

    with col1:
        st.write("### Add Author")
        auth_name = st.text_input("Author Name")
        nationality = st.text_input("Nationality (optional)")
        if st.button("Add Author"):
            conn.execute(
                "INSERT INTO Authors (AuthorName, Nationality) VALUES (?, ?)",
                (auth_name, nationality if nationality else None),
            )
            conn.commit()
            st.success(f"Author {auth_name} added!")

    with col2:
        st.write("### Add Book")
        authors = pd.read_sql("SELECT * FROM Authors", conn)
        title = st.text_input("Book Title")
        author_choice = st.selectbox(
            "Select Author",
            authors["AuthorName"].tolist() if not authors.empty else [],
        )
        copies = st.number_input("Copies", min_value=1, value=1)

        if st.button("Add Book"):
            if authors.empty or not author_choice:
                st.error("Please add/select an author before adding a book.")
            else:
                matches = authors[authors["AuthorName"] == author_choice]["AuthorID"].values
                if len(matches) == 0:
                    st.error("Selected author not found. Try adding the author again.")
                else:
                    author_id = int(matches[0])
                    conn.execute(
                "INSERT INTO Books (Title, AuthorID, AvailableCopies) VALUES (?, ?, ?)",
                (title, author_id, int(copies)),
            )
            conn.commit()
            st.success("Book added to inventory!")

elif choice == "Issue/Return":
    st.subheader("Book Transactions")
    tab1, tab2 = st.tabs(["Issue Book", "Return Book"])

    with tab1:
        books = pd.read_sql(
            "SELECT BookID, Title FROM Books WHERE AvailableCopies > 0", conn
        )
        members = pd.read_sql("SELECT MemberID, FullName FROM Members", conn)

        selected_book = st.selectbox(
            "Book", books["Title"].tolist() if not books.empty else []
        )
        selected_mem = st.selectbox(
            "Member", members["FullName"].tolist() if not members.empty else []
        )

        if st.button("Issue"):
            if books.empty or not selected_book:
                st.error("No available books to issue.")
                st.stop()
            if members.empty or not selected_mem:
                st.error("No members available. Please add members first.")
                st.stop()

            book_matches = books[books["Title"] == selected_book]["BookID"].values
            member_matches = members[members["FullName"] == selected_mem]["MemberID"].values

            if len(book_matches) == 0:
                st.error("Selected book not found in the available list.")
                st.stop()
            if len(member_matches) == 0:
                st.error("Selected member not found in the members list.")
                st.stop()

            bid = int(book_matches[0])
            mid = int(member_matches[0])
            due = date.today() + timedelta(days=14)


            conn.execute(
                "INSERT INTO Borrow (BookID, MemberID, IssueDate, DueDate) VALUES (?, ?, ?, ?)",
                (bid, mid, date.today(), due),
            )
            conn.execute(
                "UPDATE Books SET AvailableCopies = AvailableCopies - 1 WHERE BookID = ?",
                (bid,),
            )
            conn.commit()
            st.success("Book issued successfully!")

    with tab2:
        open_borrows = pd.read_sql(
            """
            SELECT BorrowID, br.IssueDate, br.DueDate, bk.Title, m.FullName
            FROM Borrow br
            JOIN Books bk ON br.BookID = bk.BookID
            JOIN Members m ON br.MemberID = m.MemberID
            WHERE br.ReturnDate IS NULL
            """,
            conn,
        )

        if open_borrows.empty:
            st.info("No active borrow records.")
        else:
            borrow_id = st.selectbox(
                "Active borrow record",
                open_borrows["BorrowID"].tolist(),
            )

            if st.button("Return"):
                # Compute fine: $1 per day overdue (example)
                row = open_borrows[open_borrows["BorrowID"] == borrow_id].iloc[0]
                due_date = row["DueDate"]
                overdue_days = max(0, (date.today() - pd.to_datetime(due_date).date()).days)
                fine = float(overdue_days)

                conn.execute(
                    "UPDATE Borrow SET ReturnDate = ?, FineAmount = ? WHERE BorrowID = ?",
                    (date.today(), fine, int(borrow_id)),
                )
                # Increment copies
                bid = int(
                    conn.execute(
                        "SELECT BookID FROM Borrow WHERE BorrowID = ?", (int(borrow_id),)
                    ).fetchone()[0]
                )
                conn.execute(
                    "UPDATE Books SET AvailableCopies = AvailableCopies + 1 WHERE BookID = ?",
                    (bid,),
                )
                conn.commit()
                st.success("Book returned successfully!")

elif choice == "Members & Fines":
    st.subheader("Members & Fines")
    tab1, tab2 = st.tabs(["Add Member", "View Fines"])

    with tab1:
        st.write("### Add Member")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        if st.button("Add Member"):
            conn.execute(
                "INSERT INTO Members (FullName, Email) VALUES (?, ?)",
                (name, email),
            )
            conn.commit()
            st.success("Member added successfully!")

    with tab2:
        fines_df = pd.read_sql(
            """
            SELECT m.FullName, SUM(br.FineAmount) AS TotalFine
            FROM Borrow br
            JOIN Members m ON br.MemberID = m.MemberID
            WHERE br.ReturnDate IS NOT NULL AND br.FineAmount > 0
            GROUP BY m.FullName
            ORDER BY TotalFine DESC
            """,
            conn,
        )
        if fines_df.empty:
            st.info("No fines recorded yet.")
        else:
            st.dataframe(fines_df, use_container_width=True)

