import { useState, useEffect } from "react";

function App() {
  const [page, setPage] = useState("home");
  const [form, setForm] = useState({ destination: "", days: 3, budget: 15000, people: 2 });
  const [tripPlan, setTripPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pastTrips, setPastTrips] = useState([]);

  const [trainForm, setTrainForm] = useState({
    from_city: "", to_city: "", date: "", preference: "balanced", check_multiple_dates: true
  });
  const [trainResult, setTrainResult] = useState(null);
  const [trainLoading, setTrainLoading] = useState(false);
  const [trainError, setTrainError] = useState(null);

  useEffect(() => {
    if (page === "past") {
      fetch("http://127.0.0.1:8000/trips")
        .then((r) => r.json())
        .then((data) => setPastTrips(data.trips));
    }
  }, [page]);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setTripPlan(null);
    try {
      const response = await fetch("http://127.0.0.1:8000/plan-trip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          destination: form.destination,
          days: Number(form.days),
          budget: Number(form.budget),
          people: Number(form.people),
        }),
      });
      const data = await response.json();
      setTripPlan(data);
    } catch (err) {
      setError("Could not connect to server. Make sure FastAPI is running!");
    }
    setLoading(false);
  };

  const loadPastTrip = async (id) => {
    const response = await fetch(`http://127.0.0.1:8000/trips/${id}`);
    const data = await response.json();
    setTripPlan(data);
    setPage("home");
  };

  const handleTrainSearch = async () => {
    setTrainLoading(true);
    setTrainError(null);
    setTrainResult(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/search-trains", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(trainForm)
      });
      const data = await res.json();
      if (data.error) setTrainError(data.error);
      else setTrainResult(data);
    } catch (e) {
      setTrainError("Could not connect to server!");
    }
    setTrainLoading(false);
  };

  const totalBudget = form.budget;

  return (
    <div style={styles.container}>
      {/* Nav */}
      <div style={styles.nav}>
        <span style={styles.navTitle}>🧳 TripSaathi</span>
        <div style={styles.navLinks}>
          <button style={page === "home" ? styles.navActive : styles.navBtn} onClick={() => setPage("home")}>Plan Trip</button>
          <button style={page === "past" ? styles.navActive : styles.navBtn} onClick={() => setPage("past")}>Past Trips</button>
          <button style={page === "trains" ? styles.navActive : styles.navBtn} onClick={() => setPage("trains")}>🚂 Trains</button>
        </div>
      </div>

      {/* HOME PAGE */}
      {page === "home" && (
        <div>
          <h1 style={styles.title}>🧳 TripSaathi</h1>
          <p style={styles.subtitle}>Your AI-powered Indian travel planner</p>

          <div style={styles.card}>
            <input style={styles.input} name="destination" placeholder="Where do you want to go? (e.g. Goa, Manali)" value={form.destination} onChange={handleChange} />
            <div style={styles.row}>
              <input style={styles.inputSmall} name="days" type="number" placeholder="Days" value={form.days} onChange={handleChange} />
              <input style={styles.inputSmall} name="people" type="number" placeholder="People" value={form.people} onChange={handleChange} />
              <input style={styles.inputSmall} name="budget" type="number" placeholder="Budget (₹)" value={form.budget} onChange={handleChange} />
            </div>
            <div style={styles.uploadBox}>
              <p style={styles.uploadLabel}>📱 Or upload a WhatsApp chat export (.txt)</p>
              <input type="file" accept=".txt" onChange={async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append("file", file);
                const res = await fetch("http://127.0.0.1:8000/parse-whatsapp", { method: "POST", body: formData });
                const data = await res.json();
                setForm({
                  destination: data.destination || form.destination,
                  days: data.days || form.days,
                  people: data.people || form.people,
                  budget: data.budget || form.budget,
                });
                alert(`✅ Extracted!\nDestination: ${data.destination}\nDays: ${data.days}\nPeople: ${data.people}\nBudget: ₹${data.budget}`);
              }} />
            </div>
            <button style={loading ? styles.buttonDisabled : styles.button} onClick={handleSubmit} disabled={loading}>
              {loading ? "Planning your trip..." : "✈️ Plan My Trip"}
            </button>
          </div>

          {error && <p style={styles.error}>{error}</p>}

          {tripPlan && (
            <div>
              <h2 style={styles.sectionTitle}>📍 {tripPlan.destination} — {tripPlan.total_days} Days for {tripPlan.total_people} People</h2>
              <p style={styles.totalCost}>Estimated Total: ₹{tripPlan.estimated_total_cost}</p>

              <div style={styles.budgetCard}>
                <p style={styles.label}>💰 Budget Usage</p>
                <div style={styles.barBg}>
                  <div style={{
                    ...styles.barFill,
                    width: `${Math.min(100, (tripPlan.estimated_total_cost / totalBudget) * 100)}%`,
                    backgroundColor: tripPlan.estimated_total_cost > totalBudget ? "#ef4444" : "#4f46e5"
                  }} />
                </div>
                <p style={styles.barLabel}>
                  ₹{tripPlan.estimated_total_cost} of ₹{totalBudget} used
                  {tripPlan.estimated_total_cost > totalBudget ? " ⚠️ Over budget!" : " ✅ Within budget"}
                </p>
                <p style={{ ...styles.label, marginTop: 16 }}>📅 Cost per Day</p>
                {tripPlan.days.map((day) => (
                  <div key={day.day} style={{ marginBottom: 8 }}>
                    <div style={styles.barRow}>
                      <span style={styles.barDayLabel}>Day {day.day} — {day.theme}</span>
                      <span style={styles.barAmount}>₹{day.estimated_cost}</span>
                    </div>
                    <div style={styles.barBg}>
                      <div style={{
                        ...styles.barFill,
                        width: `${Math.min(100, (day.estimated_cost / (totalBudget / tripPlan.total_days)) * 100)}%`,
                        backgroundColor: "#818cf8"
                      }} />
                    </div>
                  </div>
                ))}
              </div>

              <div style={styles.grid}>
                {tripPlan.days.map((day) => (
                  <div key={day.day} style={styles.dayCard}>
                    <h3 style={styles.dayTitle}>Day {day.day} — {day.theme}</h3>
                    <p style={styles.label}>📍 Places</p>
                    <ul style={styles.list}>{day.places.map((p, i) => <li key={i}>{p}</li>)}</ul>
                    <p style={styles.label}>🍽️ Food</p>
                    <ul style={styles.list}>{day.food.map((f, i) => <li key={i}>{f}</li>)}</ul>
                    <p style={styles.cost}>💰 ₹{day.estimated_cost}</p>
                  </div>
                ))}
              </div>

              <div style={styles.tipsCard}>
                <h3 style={styles.dayTitle}>💡 Travel Tips</h3>
                <ul style={styles.list}>{tripPlan.tips.map((tip, i) => <li key={i}>{tip}</li>)}</ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TRAINS PAGE */}
      {page === "trains" && (
        <div>
          <h2 style={styles.title}>🚂 Train Search</h2>
          <p style={styles.subtitle}>Find best trains with real availability</p>

          <div style={styles.card}>
            <div style={styles.row}>
              <input style={styles.inputSmall} placeholder="From (e.g. Bangalore)" value={trainForm.from_city}
                onChange={e => setTrainForm({ ...trainForm, from_city: e.target.value })} />
              <input style={styles.inputSmall} placeholder="To (e.g. Mysore)" value={trainForm.to_city}
                onChange={e => setTrainForm({ ...trainForm, to_city: e.target.value })} />
            </div>
            <div style={styles.row}>
              <input style={styles.inputSmall} type="date"
                value={trainForm.date ? trainForm.date.split("-").reverse().join("-") : ""}
                onChange={e => {
                  const parts = e.target.value.split("-");
                  setTrainForm({ ...trainForm, date: `${parts[2]}-${parts[1]}-${parts[0]}` });
                }} />
              <select style={styles.inputSmall} value={trainForm.preference}
                onChange={e => setTrainForm({ ...trainForm, preference: e.target.value })}>
                <option value="balanced">⚖️ Balanced</option>
                <option value="fast">⚡ Fastest</option>
                <option value="budget">💰 Cheapest</option>
                <option value="comfort">🛏️ Most Comfort</option>
              </select>
            </div>
            <label style={{ fontSize: 13, color: "#555", display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <input type="checkbox" checked={trainForm.check_multiple_dates}
                onChange={e => setTrainForm({ ...trainForm, check_multiple_dates: e.target.checked })} />
              Auto-find best date in next 7 days
            </label>
            <button style={trainLoading ? styles.buttonDisabled : styles.button} onClick={handleTrainSearch} disabled={trainLoading}>
              {trainLoading ? "Searching trains... (may take 30s)" : "🔍 Find Best Train"}
            </button>
          </div>

          {trainError && <p style={styles.error}>{trainError}</p>}

          {trainResult && (
            <div>
              {trainResult.dates_availability?.length > 0 && (
                <div style={styles.card}>
                  <p style={styles.label}>📅 Availability across dates</p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                    {trainResult.dates_availability.map((d, i) => (
                      <div key={i} style={{
                        padding: "6px 12px", borderRadius: 20, fontSize: 12,
                        backgroundColor: i === 0 ? "#4f46e5" : d.total_seats > 50 ? "#dcfce7" : "#fef9c3",
                        color: i === 0 ? "#fff" : "#333",
                        fontWeight: i === 0 ? "bold" : "normal"
                      }}>
                        {d.day} · {d.total_seats} seats{i === 0 ? " ✅ Best" : ""}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p style={{ ...styles.totalCost, marginBottom: 16 }}>
                Best date: {trainResult.chosen_date} · {trainResult.total_trains_checked} trains available
              </p>

              <div style={{ ...styles.dayCard, border: "2px solid #4f46e5", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={styles.dayTitle}>🥇 Best Pick</h3>
                  <span style={{ backgroundColor: "#4f46e5", color: "#fff", padding: "4px 10px", borderRadius: 20, fontSize: 12 }}>
                    Score: {trainResult.best_train.score}/100
                  </span>
                </div>
                <h2 style={{ margin: "4px 0", color: "#1a1a2e" }}>{trainResult.best_train.name}</h2>
                <p style={{ color: "#666", fontSize: 14 }}>Train #{trainResult.best_train.number}</p>
                <div style={{ ...styles.row, marginTop: 12, marginBottom: 0 }}>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>🕐 Departure</span><span style={styles.trainStatValue}>{trainResult.best_train.departure}</span></div>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>🏁 Arrival</span><span style={styles.trainStatValue}>{trainResult.best_train.arrival}</span></div>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>⏱️ Duration</span><span style={styles.trainStatValue}>{trainResult.best_train.duration}</span></div>
                </div>
                <div style={{ ...styles.row, marginTop: 12, marginBottom: 0 }}>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>🎫 Class</span><span style={styles.trainStatValue}>{trainResult.best_train.recommended_class}</span></div>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>💰 Fare</span><span style={{ ...styles.trainStatValue, color: "#16a34a" }}>{trainResult.best_train.recommended_fare}</span></div>
                  <div style={styles.trainStat}><span style={styles.trainStatLabel}>💺 Seats</span><span style={styles.trainStatValue}>{trainResult.best_train.seats_available} left</span></div>
                </div>
                <div style={{ marginTop: 12, backgroundColor: "#f0f0ff", borderRadius: 8, padding: 10 }}>
                  <p style={{ fontSize: 13, color: "#4f46e5", margin: 0 }}>💡 {trainResult.best_train.why}</p>
                </div>
              </div>

              {trainResult.second_best && (
                <div style={{ ...styles.dayCard, border: "1px solid #e5e7eb" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={styles.dayTitle}>🥈 Alternative</h3>
                    <span style={{ backgroundColor: "#e5e7eb", color: "#333", padding: "4px 10px", borderRadius: 20, fontSize: 12 }}>
                      Score: {trainResult.second_best.score}/100
                    </span>
                  </div>
                  <h2 style={{ margin: "4px 0", color: "#1a1a2e" }}>{trainResult.second_best.name}</h2>
                  <p style={{ color: "#666", fontSize: 14 }}>Train #{trainResult.second_best.number}</p>
                  <div style={{ ...styles.row, marginTop: 12, marginBottom: 8 }}>
                    <div style={styles.trainStat}><span style={styles.trainStatLabel}>🕐 Dep</span><span style={styles.trainStatValue}>{trainResult.second_best.departure}</span></div>
                    <div style={styles.trainStat}><span style={styles.trainStatLabel}>⏱️ Duration</span><span style={styles.trainStatValue}>{trainResult.second_best.duration}</span></div>
                    <div style={styles.trainStat}><span style={styles.trainStatLabel}>💰 Fare</span><span style={{ ...styles.trainStatValue, color: "#16a34a" }}>{trainResult.second_best.recommended_fare}</span></div>
                  </div>
                  <p style={{ fontSize: 13, color: "#666", margin: 0 }}>💡 {trainResult.second_best.why}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* PAST TRIPS PAGE */}
      {page === "past" && (
        <div>
          <h2 style={styles.title}>🗂️ Past Trips</h2>
          <p style={styles.subtitle}>Click any trip to reload it</p>
          {pastTrips.length === 0 && <p style={{ textAlign: "center", color: "#666" }}>No trips saved yet!</p>}
          <div style={styles.grid}>
            {pastTrips.map((trip) => (
              <div key={trip.id} style={styles.pastCard} onClick={() => loadPastTrip(trip.id)}>
                <h3 style={styles.dayTitle}>📍 {trip.destination}</h3>
                <p style={styles.pastDetail}>🗓️ {trip.days} days &nbsp;·&nbsp; 👥 {trip.people} people</p>
                <p style={styles.pastDetail}>💰 Budget: ₹{trip.budget}</p>
                <p style={styles.pastDate}>{new Date(trip.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>
                <button style={styles.reloadBtn}>Load this trip →</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { maxWidth: 900, margin: "0 auto", padding: 24, fontFamily: "sans-serif", backgroundColor: "#f5f5f5", minHeight: "100vh" },
  nav: { display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "#1a1a2e", padding: "12px 24px", borderRadius: 12, marginBottom: 24 },
  navTitle: { color: "#fff", fontSize: 18, fontWeight: "bold" },
  navLinks: { display: "flex", gap: 8 },
  navBtn: { padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "transparent", color: "#aaa", cursor: "pointer", fontSize: 14 },
  navActive: { padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "#4f46e5", color: "#fff", cursor: "pointer", fontSize: 14 },
  title: { fontSize: 32, textAlign: "center", color: "#1a1a2e", margin: "0 0 4px" },
  subtitle: { textAlign: "center", color: "#666", marginBottom: 24 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 24, boxShadow: "0 2px 8px rgba(0,0,0,0.1)", marginBottom: 24 },
  input: { width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid #ddd", marginBottom: 12, boxSizing: "border-box" },
  row: { display: "flex", gap: 12, marginBottom: 12 },
  inputSmall: { flex: 1, padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid #ddd" },
  button: { width: "100%", padding: 14, fontSize: 18, backgroundColor: "#4f46e5", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" },
  buttonDisabled: { width: "100%", padding: 14, fontSize: 18, backgroundColor: "#aaa", color: "#fff", border: "none", borderRadius: 8 },
  error: { color: "red", textAlign: "center" },
  sectionTitle: { fontSize: 22, color: "#1a1a2e", marginBottom: 4 },
  totalCost: { color: "#4f46e5", fontWeight: "bold", fontSize: 18, marginBottom: 16 },
  budgetCard: { backgroundColor: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 2px 8px rgba(0,0,0,0.08)", marginBottom: 16 },
  barBg: { backgroundColor: "#e5e7eb", borderRadius: 99, height: 10, overflow: "hidden", marginBottom: 4 },
  barFill: { height: 10, borderRadius: 99, transition: "width 0.5s ease" },
  barLabel: { fontSize: 13, color: "#666" },
  barRow: { display: "flex", justifyContent: "space-between", marginBottom: 4 },
  barDayLabel: { fontSize: 13, color: "#444" },
  barAmount: { fontSize: 13, fontWeight: "bold", color: "#4f46e5" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, marginBottom: 16 },
  dayCard: { backgroundColor: "#fff", borderRadius: 12, padding: 16, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" },
  dayTitle: { fontSize: 16, fontWeight: "bold", color: "#4f46e5", marginTop: 0, marginBottom: 8 },
  label: { fontWeight: "bold", margin: "8px 0 4px", fontSize: 14 },
  list: { paddingLeft: 18, margin: 0, fontSize: 14, color: "#444" },
  cost: { marginTop: 10, fontWeight: "bold", color: "#16a34a" },
  tipsCard: { backgroundColor: "#fff", borderRadius: 12, padding: 16, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" },
  pastCard: { backgroundColor: "#fff", borderRadius: 12, padding: 16, boxShadow: "0 2px 8px rgba(0,0,0,0.08)", cursor: "pointer" },
  pastDetail: { fontSize: 14, color: "#444", margin: "4px 0" },
  pastDate: { fontSize: 12, color: "#999", marginTop: 8 },
  reloadBtn: { marginTop: 10, padding: "8px 14px", backgroundColor: "#4f46e5", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13 },
  uploadBox: { backgroundColor: "#f0f0ff", borderRadius: 8, padding: 12, marginBottom: 12, border: "1px dashed #4f46e5" },
  uploadLabel: { fontSize: 13, color: "#4f46e5", marginBottom: 6, fontWeight: "bold" },
  trainStat: { flex: 1, display: "flex", flexDirection: "column", gap: 2 },
  trainStatLabel: { fontSize: 11, color: "#999", textTransform: "uppercase" },
  trainStatValue: { fontSize: 16, fontWeight: "bold", color: "#1a1a2e" },
};

export default App;