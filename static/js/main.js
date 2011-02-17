$(function() {
      var min_id = null;
      var max_id = null;

      function timeago (time) {
  		  var diff = (new Date().getTime() - time) / 1000;
		  var day_diff = Math.floor(diff / 86400);
          
          if (day_diff == 0) {
              if (diff < 60) return '今';
              if (diff < 3600) return Math.floor(diff / 60) + '分前';
              if (diff < 86400) return Math.floor(diff / 3600) + '時間前';
          } else if (day_diff > 0) {
              if (day_diff == 1) return '昨日';
              if (day_diff < 7) return day_diff + '日前';
              if (day_diff < 31) return Math.ceil( day_diff / 7 ) + "週間前";
          }
          var d = new Date(time);
          return d.toLocaleString();
      }
      
      function tweet_user_link(name) {
          return '<a href="http://twitter.com/' + name + '" target="twitter">@' + name + '</a>';
      }
      
      function tweet_status_link(user, status_id, datetime) {
          var caption = timeago(datetime * 1000);
          return '<i>(<a href="http://twitter.com/' + user + '/status/' + status_id + '" target="twitter" class="history-time" datetime="' + datetime + '">' + caption+ '</a>)</i>';
      }
      
      function refresh_time() {
          $(".history-time").each(
              function () {
                  var datetime = $(this).attr('datetime');
                  var now_text = $(this).text();
                  var new_text = timeago(datetime * 1000);
                  if (now_text != new_text) {
                      $(this).text(new_text);                      
                      return true;
                  } else {
                      return false;
                  }
              }
          );
      }
      
      function auto_reload() {
          load_history(-20);
      }
      
      function load_history(limit) {
          var data = {};
          var recent = true;
          if (limit < 0) {
              data['limit']  = limit;
              data['cursor'] = max_id;
          } else if (limit > 0) {
              data['limit']  = limit;
              data['cursor'] = min_id;
              recent = false;
          } else {
              data['limit'] = 20;
              limit = 0;
          }
          
          var elem = $('#history-list');
          
          $.get('api/history2', data,
               function (result) {
                   var res = eval('(' + result + ')');
                   var list = res['list'];
                   if (recent) list.reverse();
                   
                   for (var i = 0; i < list.length; i++) {
                       var from_user = list[i][0];
                       var to_user   = list[i][1];
                       var word      = list[i][2];
                       var status_id = list[i][3];
                       var datetime  = list[i][4];
                       
                       word = '<span class="word">' + word + '</span>';
                       datetime  = tweet_status_link(to_user, status_id, datetime);
                       from_user = tweet_user_link(from_user);
                       to_user   = tweet_user_link(to_user);
                       var text = from_user + ' が ' + to_user + ' に ' + word + ' といわせた ' + datetime;
                       
                       var div = $(document.createElement('div'));
                       div.html('- ' + text);
                       
                       if (recent) {
                           elem.find('div:first').before(div);
                       } else {
                           elem.find('div:last').after(div);
                       }
                       
                       if (min_id == null || status_id < min_id) {
                           min_id = status_id;
                       }
                       
                       if (max_id == null || max_id < status_id) {
                           max_id = status_id;    
                       }
                   }
                   $("#progress").hide();
                   
                   if (limit > 0 && !res['n'])  {
                       $('#history-more-see').hide();
                   } 
                   
                   if (limit < 0) {
                       if (res['n']) {
                           setTimeout(auto_reload,  3 * 1000);
                       } else {
                           setTimeout(auto_reload, 30 * 1000);
                       }
                   } else if (limit == 0) {
                       setTimeout(auto_reload, 10 * 1000);
                   }
               });
      }
      
      $("#history-more-see").click(
          function () {
              $("#progress").show();
              load_history(20);
          }
      );
      
      
      
      //
      load_history(); 
      setInterval(refresh_time, 30 * 1000);
});
