function drawChart() {
   var dataTable = new google.visualization.DataTable();
   dataTable.addColumn({ type: 'date', id: 'Date' });
   dataTable.addColumn({ type: 'number', id: 'Drivetime'});
   for (var cal in data_cal) {
           var cal_date = new Date(data_cal[cal]['date(timestamp)']);
           cal_date.setDate(cal_date.getDate() + 1);
           dataTable.addRows([[ cal_date, (Math.round(data_cal[cal]['max_value']*10)/10) ]]);
        }
   var chart = new google.visualization.Calendar(document.getElementById('calendar_basic'));
   var options = {
        title: "Tiempo de manejo por día (H)",
        allowHtml: true,
        showRowNumber: true,
        width: 1500,
        height: 350
  };

   chart.draw(dataTable, options);
   google.visualization.events.addListener(chart, 'select', selectHandler);

   function selectHandler() {

        item = chart.getSelection()[0]
        if (item.row != null) {
            var date1 = new Date(data_cal[item.row]['date(timestamp)']);
            date1.setDate(date1.getDate() + 1);
            var dd = String(date1. getDate())
            var mm = String(date1. getMonth() + 1). padStart(2, '0');
            var yyyy = date1. getFullYear();
            date1 = dd + '/' + mm + '/' + yyyy;
            console.log(date1);
            document.getElementById('d1_input').value = date1;
            document.getElementById('d2_input').value = date1;
            document.getElementById('Mainform').submit();
        }
    }
}