export default function SignupPage() {
  return (
    <div
      style={{
        maxWidth: "500px",
        margin: "100px auto",
        padding: "40px",
        border: "1px solid #ccc",
      }}
    >
      <h1>Create Account</h1>

      <div
        style={{
          marginTop: "30px",
          padding: "20px",
          backgroundColor: "#f0f8ff",
          border: "1px solid #0070f3",
          borderRadius: "4px",
        }}
      >
        <p style={{ margin: 0, lineHeight: "1.6" }}>
          <strong>
            Accounts are created automatically after
            purchase.
          </strong>
        </p>
        <p
          style={{
            marginTop: "15px",
            marginBottom: 0,
            lineHeight: "1.6",
          }}
        >
          After completing your purchase, you'll receive an
          email with your login credentials and instructions
          to access your DataWoven account.
        </p>
      </div>

      <div
        style={{ marginTop: "30px", textAlign: "center" }}
      >
        <p style={{ marginBottom: "10px" }}>
          Already have an account?
        </p>
        <a
          href="/login"
          style={{
            color: "#0070f3",
            fontWeight: "bold",
            fontSize: "16px",
          }}
        >
          Sign in here
        </a>
      </div>
    </div>
  );
}
