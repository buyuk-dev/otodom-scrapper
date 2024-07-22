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
        tableContainer.style.flex = `0 0 ${window.innerWidth - event.rect.width - 20}px`;

        Object.assign(event.target.dataset, { x, y });
    });
});

function loadTableData(apartments) {
    const container = document.getElementById('handsontable-container');

    function parseNumber(str) {
        const match = str.match(/^(\d+(\.\d+)?)/);
        return match ? parseFloat(match[0]) : undefined;
    }

    const data = apartments.map(apartment => [
        apartment.gpt.Title,
        apartment.gpt.Location,
        parseNumber(apartment.gpt.Size),
        parseNumber(apartment.gpt.Price.Rent) + parseNumber(apartment.gpt.Price.Administrative),
        parseNumber(apartment.gpt.Price.Rent),
        parseNumber(apartment.gpt.Price.Administrative),
        apartment.gpt.URL
    ]);

    const hot = new Handsontable(container, {
        data: data,
        colHeaders: ['Title', 'Location', 'Size', 'Total Price', 'Rent Price', 'Administrative Costs', 'URL'],
        columns: [
            { type: 'text' },
            { type: 'text' },
            { type: 'numeric', numericFormat: { pattern: '0,0' } },
            { type: 'numeric', numericFormat: { pattern: '0,0' } },
            //{ type: 'text' },
            //{ type: 'text' },
            { type: 'numeric', numericFormat: { pattern: '0,0' } },
            { type: 'numeric', numericFormat: { pattern: '0,0' } },
            {
                renderer: urlRenderer,
                readOnly: true
            }
        ],
        stretchH: 'all',
        autoColumnSize: true,
        manualColumnResize: true,
        manualRowResize: true,
        columnSorting: true,
        filters: true,
        dropdownMenu: true,
        afterSelectionEnd: function (row, col, row2, col2) {
            if (row === row2 && col === col2) { // Ensure single cell selection
                // When a row is selected, fetch and render the ad details
                const visualRowIndex = this.toPhysicalRow(row);
                const selectedData = data[visualRowIndex];
                const url = selectedData[6]; // Ensure this is the correct column for URL
                showAdDetails(url);
            }
        },
        licenseKey: 'non-commercial-and-evaluation'  // Set the license key
    });

    function urlRenderer(instance, td, row, col, prop, value, cellProperties) {
        Handsontable.renderers.TextRenderer.apply(this, arguments);
        td.innerHTML = `<a href="${value}" target="_blank">open</a>`;
    }
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
    const hot = Handsontable.getInstance(document.getElementById('handsontable-container'));

    hot.addHook('afterGetColHeader', function (col, TH) {
        if (col === 1) { // Assuming 'Location' is the second column
            const instance = this;
            TH.innerHTML = `<input type="text" class="handsontable-input-filter" placeholder="Filter location">`;
            TH.querySelector('input').addEventListener('keyup', function (event) {
                instance.getPlugin('Filters').addCondition(col, 'contains', [event.target.value]);
                instance.getPlugin('Filters').filter();
            });
        }
    });
    hot.render();
}

function sortTable(columnIndex) {
    const hot = Handsontable.getInstance(document.getElementById('handsontable-container'));
    hot.getPlugin('ColumnSorting').sort({ column: columnIndex, sortOrder: 'asc' });
}