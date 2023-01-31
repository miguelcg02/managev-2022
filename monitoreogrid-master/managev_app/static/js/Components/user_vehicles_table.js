function drawTable() {
    const data = new google.visualization.DataTable();

    data.addColumn('number', 'Modelo');
    data.addColumn('string', 'Placa');
    data.addColumn('string', 'Marca');
    data.addColumn('number', 'Odometro');

    data_vehicles.forEach(vehicle => {
        if (vehicle.activo) {
            data.addRows([[
                {v: vehicle.year, p: {style: 'background-color: #58b2ff;'}},
                {v: vehicle.placa, p: {style: 'background-color: #58b2ff;'}},
                {v: vehicle.marca, p: {style: 'background-color: #58b2ff;'}},
                {v: vehicle.odometer, p: {style: 'background-color: #58b2ff;'}},
            ]]);
        }

        else {
            data.addRows([[
                vehicle.year,
                vehicle.placa,
                vehicle.marca,
                vehicle.odometer
            ]]);
        }
    })

    var table = new google.visualization.Table(document.getElementById('table_div'));
    var options = {
        allowHtml: true,
        showRowNumber: true,
        width: '100%',
        cssClassNames: {
          tableCell: 'small-font'
        }
      };
    table.draw(data, options);

    //{showRowNumber: true, width: '100%', height: '2000%'}
    google.visualization.events.addListener(table, 'select', selectHandler);
           function selectHandler() {
                item = table.getSelection()[0]
                if (item.row != null) {
                    console.log(data_vehicles[item.row]);

                    req2 = $.ajax({
                            url : "/update_vehicle/" + data_vehicles[item.row]['placa'],
                            type : "GET",
                        });

                    req2.done(function(res) {

                        if (res === 1) {
                            console.log('activo');
                        } else {
                            console.log('no_activo');
                            window.location.reload();
                        }
                    });
                }
            }
    }