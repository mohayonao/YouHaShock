$(function() {
    var history_page = 0;
    
    function add_history(data) {
        var div = $(document.createElement('div'));
        div.html('- ' + data);
        $('#history-list').append(div);
    }
    
    function load_history(page) {
        $("#progress").show();
        $.get('api/history', { 'page': page },
              function (result) {
                  var data = eval('(' + result + ')');
                  for (var i in data) {
                      add_history(data[i]);
                  }
                  if (data.length < 15) {
                      $("#history-more-see").hide();
                  } else {
                      history_page++;             
                  }
                  $("#progress").hide();
              });
    }
    
    $("#history-more-see").click(
        function () {
            load_history(history_page);
        });
    
    load_history(0);
});
