// Custom JS Goes HERE
let theFile = null;
const data = {};
const selectors = {

}

function spinnerStart(callback) {
    var spinner = new Spinner().spin();
    $('body').append(spinner.el);
    if (callback) callback();
}

function spinnerStop(callback) {
    $('body .spinner').remove();
    if (callback) callback();
}

function createSelectors(channelnames, sitenames, binnames) {
    let $grid = $('#selectors')
    if ($grid.length > 0) return

    $grid = $('<div id="selectors" class="grid-x grid-margin-x"></div>')

    const $buttoncell = $('<div class="small-2 cell"></div>');
    if (theFile && theFile == 'binned.json') $buttoncell.append('<a href="incremental.html" class="large button">Incremental</a>');
    else $buttoncell.append('<a href="index.html" class="large button">Binned</a>');

    const $channelCell = $('<div class="small-3 cell"></div>');
    const $channelSelector = $('<select multiple="true" id="channel-selector" name="Channel" placeholder="Channel"></select>')
    channelnames.forEach(cn => $channelSelector.append(`<option value="${cn}">${cn}</option>`))
    $channelCell.append($channelSelector)

    const $siteCell = $('<div class="small-2 cell"></div>');
    const $siteSelector = $('<select multiple="true" id="site-selector" name="Site" placeholder="Site"></select>')
    sitenames.forEach(sn => $siteSelector.append(`<option value="${sn}">${sn}</option>`))
    $siteCell.append($siteSelector)

    const $binCell = $('<div class="small-3 cell"></div>');
    const $binSelector = $('<select multiple="true" id="bin-selector" name="Bin" placeholder="Bin"></select>')
    binnames.forEach(bn => $binSelector.append(`<option value="${bn}">${bn}</option>`))
    $binCell.append($binSelector)

    const $areavolCell = $('<div class="small-2 cell"></div>');
    const $areaVolSelector = $('<select multiple="true" id="areavol-selector" name="Area or Volume" placeholder="Area or Volume"><option value="Area">Area</option><option value="Volume">Volume</option></select>')
    $areavolCell.append($areaVolSelector)

    $grid.append($buttoncell).append($channelCell).append($siteCell).append($binCell).append($areavolCell)

    $("#main section").append($grid)

    $channelSelector.selectize().on('change', val => {
        selectors['channel'] = val.target.selectize.getValue()
        spinnerStart(manySmallGraphs);
    });
    $siteSelector.selectize().on('change', val => {
        selectors['site'] = val.target.selectize.getValue()
        spinnerStart(manySmallGraphs);
    });
    $binSelector.selectize().on('change', val => {
        selectors['bin'] = val.target.selectize.getValue()
        spinnerStart(manySmallGraphs);
    });
    $areaVolSelector.selectize().on('change', val => {
        selectors['areavol'] = val.target.selectize.getValue()
        spinnerStart(manySmallGraphs);
    });
}



function getJSON(file, callback) {
    theFile = file;
    $.ajax(file, {
        type: 'GET',
        contentType: "application/json",
        success: function (res) {
            if (typeof (res) == "object") {
                data.raw = res.data;
                data.xy = {
                    x: res.meta["147"],
                    y: res.meta["148"]
                }
            } else {
                // sometimes S3 returns the wrong mime type. I'm too lazy to figure this out.
                data.inventory = JSON.parse(res)
            }
            callback();
        },
        error: function (e) {
            console.log('ERROR: Lambda returned error\n\n' + e.responseText);
        },
    });
}

function bigGraphPopup(channelKey, siteKey, binkey, areavol) {
    const $modal = $('<div class="reveal" id="BigGraphModal" data-reveal></div>');
    const $close = $('<button class="close-button" data-close aria-label="Close reveal" type="button"><span aria-hidden="true">&times;</span></button>');
    $modal.append(`<h3>${areavol} - ${channelKey} - ${siteKey} - ${binkey}</h3>`).append($close);
    const $chartdiv = $('<div></div>');
    $modal.append($chartdiv);
    try {
        const test = data.raw[channelKey][siteKey][binkey];
        makeBigPlot($chartdiv, channelKey, siteKey, binkey, areavol);
    } catch (e) {}
    const elem = new Foundation.Reveal($modal, {
        closeOnClick: false,
        closeOnEsc: true,
        fullScreen: true,
        multipleOpened: false,
        overlay: true,
        resetOnClose: true
    })
    elem.open();
    $(window).on(
        'closeme.zf.reveal', () => {
            $modal.remove();
        }
    );
}

function PlotStarter(file) {
    spinnerStart();
    $('#main section #grid').remove();
    if (data.raw) {
        manySmallGraphs();
        spinnerStop();
    } else {
        getJSON(file, manySmallGraphs);
    }
}

function manySmallGraphs() {
    $('#main section table').remove();
    const sitetables = {};
    const sitenames = [];
    const binnames = [];
    const channelnames = [];

    Object.keys(data.raw).forEach(channelKey => {
        if (channelnames.indexOf(channelKey) < 0) channelnames.push(channelKey);
        Object.keys(data.raw[channelKey]).forEach(siteKey => {
            if (sitenames.indexOf(siteKey) < 0) sitenames.push(siteKey);
            Object.keys(data.raw[channelKey][siteKey]).forEach(binkey => {
                if (binnames.indexOf(binkey) < 0) binnames.push(binkey);
            });
        });
    });

    createSelectors(channelnames, sitenames, binnames);

    Object.keys(data.raw).forEach(channelKey => {
        if (selectors.channel && selectors.channel.length > 0 && selectors.channel.indexOf(channelKey) < 0) return
        Object.keys(data.raw[channelKey]).forEach(siteKey => {
            if (selectors.site && selectors.site.length > 0 && selectors.site.indexOf(siteKey) < 0) return
            let hasheaders = true;
            if (!sitetables[siteKey]) {
                const $table = $("<table></table>");
                const $thead = $("<thead></thead>");
                const $tbody = $("<tbody></tbody>");
                const $thr1 = $(`<tr class='thr1'><td class="sitename" rowspan=2>${siteKey}</td></tr>`);
                const $thr2 = $("<tr class='thr2'></tr>");
                $thead.append($thr1).append($thr2);
                $table.append($thead).append($tbody);
                hasheaders = false;
                sitetables[siteKey] = $table;
                $("#main section").append($table);
            }
            const $useTable = sitetables[siteKey];

            const $chrow = $(`<tr><td>${channelKey}</td></tr>`);
            $useTable.append($chrow);

            ["Area", "Volume"].forEach(areavol => {
                const filteredbins = binnames.filter(bk => !selectors.bin || selectors.bin.length == 0 || selectors.bin.indexOf(bk) > -1)
                if (selectors.areavol && selectors.areavol.length > 0 && selectors.areavol.indexOf(areavol) < 0) return
                if (!hasheaders) {
                    $useTable.find('tr.thr1').append(`<td class="${areavol}" colspan=${filteredbins.length}>${areavol}</td>`)
                    filteredbins.map(bk => $useTable.find('tr.thr2').append(`<td class='${areavol}'>${bk}</td>`));
                }

                filteredbins.forEach(binkey => {
                    const $col = $(`<td></td>`).addClass(`xygraphs ${areavol}`);
                    const $coldiv = $('<div></div>');
                    $col.append($coldiv);
                    $chrow.append($col);   
                    try {
                        const test = data.raw[channelKey][siteKey][binkey];
                        makePlot($coldiv, channelKey, siteKey, binkey, areavol);
                        $col.click(bigGraphPopup.bind(null, channelKey, siteKey, binkey, areavol))
                    } catch (err) {}
                });
            });
        });
    })

    spinnerStop();
}

function create_data(channel, site, binname, areavol) {
    const x = [];
    const y = [];
    const dates = [];
    const elev = [];
    let n = 0;
    let x_mean = 0;
    let y_mean = 0;
    let term1 = 0;
    let term2 = 0;


    Object.keys(data.raw[channel][site][binname]).forEach(datestr => {
        let dSourceObj = data.raw[channel][site][binname][datestr];
        // try binned first
        if (dSourceObj[data.xy.x] && dSourceObj[data.xy.y]) {
            dates.push(datestr);
            const xval = dSourceObj[data.xy.x][areavol];
            const yval = dSourceObj[data.xy.y][areavol];
            x.push(xval);
            y.push(yval);
            x_mean += xval;
            y_mean += yval;
            n++;
        }
        // Maybe we're incremental
        else {
            Object.keys(dSourceObj).forEach(el => {
                if (dSourceObj[el][data.xy.x] && dSourceObj[el][data.xy.y]) {
                    elev.push(el);
                    dates.push(datestr);
                    const xval = dSourceObj[el][data.xy.x][areavol];
                    const yval = dSourceObj[el][data.xy.y][areavol];
                    x.push(xval);
                    y.push(yval);
                    x_mean += xval;
                    y_mean += yval;
                    n++;
                }
            })
        }
    });

    if (n == 0) return [];

    // calculate mean x and y
    x_mean /= n;
    y_mean /= n;

    // calculate coefficients
    let xr = 0;
    let yr = 0;
    for (i = 0; i < x.length; i++) {
        xr = x[i] - x_mean;
        yr = y[i] - y_mean;
        term1 += xr * yr;
        term2 += xr * xr;
    }
    let b1 = term1 / term2;
    let b0 = y_mean - (b1 * x_mean);

    // perform regression 
    yhat = [];
    // fit line using coeffs
    for (i = 0; i < x.length; i++) {
        const val = b0 + (x[i] * b1);
        yhat.push(val);
    }

    const newData = [];
    for (i = 0; i < y.length; i++) {
        newData.push({
            "date": dates[i] || "",
            "elev": elev[i] || null,
            "yhat": yhat[i] || 0,
            "y": y[i] || 0,
            "x": x[i] || 0
        })
    }
    return (newData);
}


function makePlot($container, channel, site, binname, areavol) {

    // Empty buckets to be filled
    const cleanedData = create_data(channel, site, binname, areavol);

    const margin = {
            top: 10,
            right: 10,
            bottom: 30,
            left: 30
        },
        realwidth = $container.width() < 200 ? $container.width() : 200;
        width =  200 - margin.left - margin.right,
        height = 200 - margin.top - margin.bottom;

    const x = d3.scaleLinear().range([0, width]);
    const y = d3.scaleLinear().range([height, 0]);

    const xAxis = d3.axisBottom().scale(x);
    const yAxis = d3.axisLeft().scale(y);

    const svg = d3.select($container[0]).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    const line = d3.line()
        .x(d => x(d.x))
        .y(d => y(d.yhat));

    x.domain(d3.extent(cleanedData, d => d.x));
    y.domain(d3.extent(cleanedData, d => d.y));

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("class", "axislabel")
        .attr("x", width)
        .attr("y", -6)
        .style("text-anchor", "end")
        .attr("fill", "black")
        .text(data.xy.x);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("class", "axislabel")
        .attr("transform", "rotate(-90)")
        .attr("y", 10)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .attr("fill", "black")
        .text(data.xy.y)

    svg.append("path")
        .datum(cleanedData)
        .attr("class", "line")
        .attr("d", line);

    // svg.append("text")
    //     .attr("x", (width / 2))             
    //     .attr("y", 10)
    //     .attr("class", "charttitle")
    //     .attr("text-anchor", "middle")  
    //     .style("text-decoration", "underline")  
    //     .text(`${areavol} - ${binname}`);

    svg.selectAll(".dot")
        .data(cleanedData)
        .enter().append("circle")
        .attr("class", "dot")
        .attr("r", 1.5)
        .attr("cx", d => x(d.x))
        .attr("cy", d => y(d.y))

}


function makeBigPlot($container, channel, site, binname, areavol) {

    // Empty buckets to be filled
    const cleanedData = create_data(channel, site, binname, areavol);


    const margin = {
            top: 10,
            right: 10,
            bottom: 30,
            left: 30
        },
        width = 600 - margin.left - margin.right,
        height = 600 - margin.top - margin.bottom;

    const x = d3.scaleLinear().range([0, width]);
    const y = d3.scaleLinear().range([height, 0]);

    const xAxis = d3.axisBottom().scale(x);
    const yAxis = d3.axisLeft().scale(y);

    const svg = d3.select($container[0]).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    const line = d3.line()
        .x(d => x(d.x))
        .y(d => y(d.yhat));

    x.domain(d3.extent(cleanedData, d => d.x));
    y.domain(d3.extent(cleanedData, d => d.y));

    // Define the div for the tooltip
    const popdiv = d3.select($container[0]).append("div")
        .attr("class", "datatips")
        .style("opacity", 0);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("class", "axislabel")
        .attr("x", width)
        .attr("y", -6)
        .style("text-anchor", "end")
        .attr("fill", "black")
        .text(data.xy.x);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("class", "axislabel")
        .attr("transform", "rotate(-90)")
        .attr("y", 10)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .attr("fill", "black")
        .text(data.xy.y)

    svg.append("path")
        .datum(cleanedData)
        .attr("class", "line")
        .attr("d", line);

    svg.selectAll(".dot")
        .data(cleanedData)
        .enter().append("circle")
        .attr("class", "dot")
        .attr("r", 3.5)
        .attr("cx", d => x(d.x))
        .attr("cy", d => y(d.y))
        .on("mouseover", d => {
            console.log("hover");
            const $bucket = $('<div></div>');
            $bucket.append(`<div class="grid-x grid-margin-x"><div class="small-4 cell"><strong>Date</strong></div><div class="small-8 cell">${d.date}</div></div>`);

            if (d.elev) {
                $bucket.append(`<div class="grid-x grid-margin-x"><div class="small-5 cell"><strong>Elev.</strong></div><div class="small-7 cell">${d.elev}</div></div>`);
            }
            $bucket.append(`<div class="grid-x grid-margin-x"><div class="small-5 cell"><strong>${areavol} ${data.xy.x}</strong></div><div class="small-7 cell">${d.x}</div></div>`);
            $bucket.append(`<div class="grid-x grid-margin-x"><div class="small-5 cell"><strong>${areavol} ${data.xy.y}</strong></div><div class="small-7 cell">${d.y}</div></div>`);
            popdiv.transition()
                .duration(100)
                .style("opacity", 1);
            popdiv.html($bucket.html())
                .style("left", (d3.event.offsetX) + "px")
                .style("top", (d3.event.offsetY - 28) + "px");
        })
        .on("mouseout", d => {
            popdiv.transition()
                .duration(300)
                .style("opacity", 0);
        });

}