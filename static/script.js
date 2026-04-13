const demoData = {
  labs: [
    { lab_id: 301, lab_name: "Database Lab", department: "CSE", location: "Block A - Floor 2", total_pcs: 24, lab_incharge: "Dr. Rao", contact: "rao@college.edu" },
    { lab_id: 302, lab_name: "Networking Lab", department: "IT", location: "Block B - Floor 1", total_pcs: 18, lab_incharge: "Prof. Mehta", contact: "mehta@college.edu" },
    { lab_id: 303, lab_name: "Programming Lab", department: "CSE", location: "Block A - Floor 3", total_pcs: 30, lab_incharge: "Dr. Sen", contact: "sen@college.edu" }
  ],
  pcs: [
    { pc_id: 1, pc_number: "DB-301-01", processor: "Intel i5 12th Gen", ram: 16, storage: 512, operating_system: "Windows 11", status: "Active", health_score: 94, lab_id: 301 },
    { pc_id: 2, pc_number: "DB-301-02", processor: "Intel i5 11th Gen", ram: 8, storage: 256, operating_system: "Windows 10", status: "Maintenance", health_score: 68, lab_id: 301 },
    { pc_id: 3, pc_number: "NET-302-04", processor: "AMD Ryzen 5", ram: 16, storage: 512, operating_system: "Ubuntu 22.04", status: "Active", health_score: 91, lab_id: 302 },
    { pc_id: 4, pc_number: "NET-302-09", processor: "Intel i3 10th Gen", ram: 8, storage: 256, operating_system: "Windows 10", status: "Faulty", health_score: 41, lab_id: 302 },
    { pc_id: 5, pc_number: "PROG-303-17", processor: "Intel i7 12th Gen", ram: 16, storage: 1024, operating_system: "Windows 11", status: "Active", health_score: 97, lab_id: 303 }
  ],
  software: [
    { software_id: 1, software_name: "MySQL Workbench", version: "8.0.42", license_type: "Community", expiry_date: "2027-12-31" },
    { software_id: 2, software_name: "PyCharm Professional", version: "2025.3", license_type: "Academic", expiry_date: "2026-04-20" },
    { software_id: 3, software_name: "Cisco Packet Tracer", version: "8.2.2", license_type: "Institutional", expiry_date: "2026-04-08" },
    { software_id: 4, software_name: "MATLAB Campus", version: "R2025b", license_type: "Campus", expiry_date: "2026-03-30" }
  ],
  maintenance: [
    { maintenance_id: 9001, issue_description: "Keyboard not working", reported_date: "2026-03-27", resolved_date: "2026-03-28", status: "Resolved", pc_id: 1, reported_by: "Anita Sharma" },
    { maintenance_id: 9002, issue_description: "Slow boot performance", reported_date: "2026-04-01", resolved_date: null, status: "Pending", pc_id: 2, reported_by: "Rohit Das" },
    { maintenance_id: 9003, issue_description: "LAN port failure", reported_date: "2026-04-03", resolved_date: null, status: "Pending", pc_id: 4, reported_by: "Sneha Gupta" }
  ],
  users: [
    { user_id: 11, name: "Surabhi Singh", email: "surabhi@college.edu", role: "Admin" },
    { user_id: 12, name: "Rohit Das", email: "rohit@college.edu", role: "Lab Assistant" },
    { user_id: 13, name: "Anita Sharma", email: "anita@college.edu", role: "Faculty" }
  ]
};

function parseDate(dateStr) {
  return new Date(`${dateStr}T00:00:00`);
}

function getSoftwareStatus(expiryDate) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = parseDate(expiryDate);
  const diff = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));

  if (diff < 0) return { label: "Expired", cls: "status-expired" };
  if (diff <= 30) return { label: "Expiring Soon", cls: "status-expiring" };
  return { label: "Valid", cls: "status-valid" };
}

function statusPill(status) {
  const s = String(status || "").toLowerCase();
  if (s === "active" || s === "resolved" || s === "valid") return "status-active";
  if (s === "maintenance" || s === "expiring soon") return "status-maintenance";
  if (s === "faulty" || s === "expired" || s === "pending") return "status-faulty";
  return "status-maintenance";
}

function fillDashboard() {
  const labsCount = document.getElementById("labsCount");
  const pcsCount = document.getElementById("pcsCount");
  const softwareCount = document.getElementById("softwareCount");
  const maintenanceCount = document.getElementById("maintenanceCount");
  const expiryAlerts = document.getElementById("expiryAlerts");

  if (labsCount && Number(labsCount.textContent.trim()) === 0) labsCount.textContent = demoData.labs.length;
  if (pcsCount && Number(pcsCount.textContent.trim()) === 0) pcsCount.textContent = demoData.pcs.length;
  if (softwareCount && Number(softwareCount.textContent.trim()) === 0) softwareCount.textContent = demoData.software.length;
  if (maintenanceCount && Number(maintenanceCount.textContent.trim()) === 0) {
    maintenanceCount.textContent = demoData.maintenance.filter((m) => m.status === "Pending").length;
  }

  if (expiryAlerts && expiryAlerts.children.length <= 1) {
    const alerts = demoData.software
      .map((item) => ({ item, status: getSoftwareStatus(item.expiry_date) }))
      .filter((x) => x.status.label !== "Valid")
      .slice(0, 4);

    expiryAlerts.innerHTML = alerts.length
      ? alerts.map((x) => `<div class="alert-item"><strong>${x.item.software_name}</strong> <span class="status-pill ${x.status.cls} ms-2">${x.status.label}</span><div class="small text-secondary mt-1">Expiry: ${x.item.expiry_date}</div></div>`).join("")
      : '<p class="text-secondary mb-0">No licenses expiring in the next 30 days.</p>';
  }

  const canvas = document.getElementById("pcStatusChart");
  if (canvas && window.Chart) {
    const active = demoData.pcs.filter((pc) => pc.status === "Active").length;
    const faulty = demoData.pcs.filter((pc) => pc.status === "Faulty").length;
    const maintenance = demoData.pcs.filter((pc) => pc.status === "Maintenance").length;

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: ["Active", "Faulty", "Maintenance"],
        datasets: [{
          data: [active, faulty, maintenance],
          backgroundColor: ["#1f9d63", "#c94141", "#d68b00"],
          borderWidth: 0
        }]
      },
      options: {
        plugins: { legend: { position: "bottom" } },
        cutout: "62%"
      }
    });
  }
}

function fillLabs() {
  const tbody = document.getElementById("labsTableBody");
  if (!tbody || tbody.children.length) return;
  tbody.innerHTML = demoData.labs.map((lab) => `
    <tr>
      <td>${lab.lab_id}</td>
      <td>${lab.lab_name}</td>
      <td>${lab.department}</td>
      <td>${lab.location}</td>
      <td>${lab.lab_incharge}</td>
      <td>${lab.total_pcs}</td>
      <td>${lab.contact}</td>
      <td><a class="btn btn-sm btn-app-outline" href="/lab/${lab.lab_id}">View</a></td>
    </tr>
  `).join("");
}

function fillLabDetail() {
  const tbody = document.getElementById("labDetailPcBody");
  if (!tbody || tbody.children.length) return;
  const selectedLab = demoData.labs[0];
  const pcs = demoData.pcs.filter((pc) => pc.lab_id === selectedLab.lab_id);

  const map = {
    labNameTitle: selectedLab.lab_name,
    labIdValue: selectedLab.lab_id,
    labDepartmentValue: selectedLab.department,
    labLocationValue: selectedLab.location,
    labPcsValue: selectedLab.total_pcs,
    labInchargeValue: selectedLab.lab_incharge
  };
  Object.entries(map).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  });

  tbody.innerHTML = pcs.map((pc) => `
    <tr>
      <td>${pc.pc_number}</td>
      <td>${pc.processor}</td>
      <td>${pc.ram} GB</td>
      <td>${pc.storage} GB</td>
      <td>${pc.operating_system}</td>
      <td><span class="status-pill ${statusPill(pc.status)}">${pc.status}</span></td>
      <td>
        <div class="health-wrap">
          <div class="health-bar"><div class="health-fill" style="width:${pc.health_score}%"></div></div>
          <small class="text-secondary fw-semibold">${pc.health_score}%</small>
        </div>
      </td>
    </tr>
  `).join("");
}

function fillPcs() {
  const tbody = document.getElementById("pcsTableBody");
  if (!tbody || tbody.children.length) return;
  tbody.innerHTML = demoData.pcs.map((pc) => `
    <tr>
      <td>${pc.pc_number}</td>
      <td>${pc.lab_id}</td>
      <td>${pc.processor}</td>
      <td>${pc.ram} GB</td>
      <td>${pc.storage} GB</td>
      <td>${pc.operating_system}</td>
      <td><span class="status-pill ${statusPill(pc.status)}">${pc.status}</span></td>
      <td>
        <div class="health-wrap">
          <div class="health-bar"><div class="health-fill" style="width:${pc.health_score}%"></div></div>
          <small class="text-secondary fw-semibold">${pc.health_score}%</small>
        </div>
      </td>
    </tr>
  `).join("");
}

function fillSoftware() {
  const tbody = document.getElementById("softwareTableBody");
  if (!tbody || tbody.children.length) return;
  tbody.innerHTML = demoData.software.map((item) => {
    const state = getSoftwareStatus(item.expiry_date);
    return `
      <tr>
        <td>${item.software_name}</td>
        <td>${item.version}</td>
        <td>${item.license_type}</td>
        <td>${item.expiry_date}</td>
        <td><span class="status-pill ${statusPill(state.label)}">${state.label}</span></td>
      </tr>
    `;
  }).join("");
}

function fillMaintenance() {
  const tbody = document.getElementById("maintenanceTableBody");
  if (!tbody || tbody.children.length) return;
  tbody.innerHTML = demoData.maintenance.map((rec) => `
    <tr>
      <td>${rec.issue_description}</td>
      <td>${rec.pc_id}</td>
      <td>${rec.reported_date}</td>
      <td>${rec.resolved_date || "-"}</td>
      <td><span class="status-pill ${statusPill(rec.status)}">${rec.status}</span></td>
      <td>${rec.reported_by}</td>
    </tr>
  `).join("");
}

function fillUsers() {
  const tbody = document.getElementById("usersTableBody");
  if (!tbody || tbody.children.length) return;
  tbody.innerHTML = demoData.users.map((u) => `
    <tr>
      <td>${u.name}</td>
      <td>${u.email}</td>
      <td>${u.role}</td>
      <td><span class="status-pill status-active">Active</span></td>
    </tr>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  const navKey = page === "lab-detail" ? "labs" : page;
  document.querySelectorAll(".menu-link").forEach((link) => {
    if (link.dataset.nav === navKey) link.classList.add("active");
  });

  if (page === "dashboard") fillDashboard();
  if (page === "labs") fillLabs();
  if (page === "lab-detail") fillLabDetail();
  if (page === "pcs") fillPcs();
  if (page === "software") fillSoftware();
  if (page === "maintenance") fillMaintenance();
  if (page === "users") fillUsers();
});
