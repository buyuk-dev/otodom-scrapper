document.addEventListener('DOMContentLoaded', () => {
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            loadTableData(data);
        });

    // Initialize interact.js for resizable sidebar
    interact('#sidebar').resizable({
        edges: { left: true },
        modifiers: [
            interact.modifiers.restrictEdges({
                outer: 'parent',
                endOnly: true,
            }),
            interact.modifiers.restrictSize({
                min: { width: 150 },
                max: { width: window.innerWidth - 100 }
            })
        ],
        inertia: true
    }).on('resizemove', function (event) {
        let { x, y } = event.target.dataset;

        x = (parseFloat(x) || 0) + event.deltaRect.left;

        Object.assign(event.target.style, {
            width: `${event.rect.width}px`
        });

        // Adjust the main table container width
        const tableContainer = document.querySelector('.table-container');
        tableContainer.style.flex = `0 0 ${window.innerWidth - event.rect.width - 10}px`;

        Object.assign(event.target.dataset, { x, y });
    });
});

function loadTableData(apartments) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    apartments.forEach((apartment, index) => {
        let row = `
            <tr onclick="showAdDetails('${apartment.gpt.URL}', ${index})">
                <td>${apartment.gpt.Title}</td>
                <td>${apartment.gpt.Location}</td>
                <td>${apartment.gpt.Size}</td>
                <td>${apartment.gpt.Price.Rent} zł</td>
                <td>${apartment.gpt.Price.Administrative} zł</td>
                <td><a href="${apartment.gpt.URL}" target="_blank">View Listing</a></td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

function showAdDetails(url, index) {
    console.log(`Fetching HTML for URL: ${url}`);
    fetch(`/fetch-html?url=${encodeURIComponent(url)}`)
        .then(response => response.text())
        .then(html => {
            const iframe = document.getElementById('adIframe');
            iframe.srcdoc = '';  // Clear existing content
            iframe.srcdoc = html;  // Set new content
        })
        .catch(error => {
            console.error('Error fetching HTML:', error);
            const iframe = document.getElementById('adIframe');
            iframe.srcdoc = '<p>Error fetching the ad details.</p>';
        });
}

function filterTable() {
    const filter = document.getElementById('locationFilter').value.toUpperCase();
    const rows = document.getElementById('tableBody').getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const location = cells[1].textContent || cells[1].innerText;
        if (location.toUpperCase().indexOf(filter) > -1) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}

function sortTable(columnIndex) {
    const table = document.getElementById('apartmentTable');
    let switching = true;
    let shouldSwitch;
    let rows, x, y;
    let switchCount = 0;
    let direction = "asc";

    while (switching) {
        switching = false;
        rows = table.rows;

        for (let i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("TD")[columnIndex];
            y = rows[i + 1].getElementsByTagName("TD")[columnIndex];

            if (direction === "asc") {
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            } else if (direction === "desc") {
                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchCount++;
        } else {
            if (switchCount === 0 && direction === "asc") {
                direction = "desc";
                switching = true;
            }
        }
    }
}