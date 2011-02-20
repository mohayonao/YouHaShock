$(function() {
      
      // YOUはSHOCK!!
      $("#use").click(
          function () {
              $(this)
                  .attr('disabled', 'true')
                  .removeClass('enabled-btn')
                  .addClass('disabled-btn');
              $("#v-progress").show();
              location.href = '/verify';
          });
      
      
      // アイコンの管理 ////////////////////////////////////////////////////////
      var user_icons = {};
      function get_user_icons(name) {
          if (typeof(user_icons[name]) == 'undefined') {
              user_icons[name] = null;
              var data = { name: name };
              $.get('/api/image', data,
                    function (result) {
                        if (result != 'null') {
                            user_icons[name] = result;
                            set_user_icon(name);
                        }
                    });
          } else {
              set_user_icon(name);
          }
      }
      
      
      function set_user_icon(name) {
          if (user_icons[name]) {
              $("#call img[name='" + name + "']").each(
                  function () { $(this).attr('src', user_icons[name]); });
              $("#callee img[name='" + name + "']").each(
                  function () { $(this).attr('src', user_icons[name]); });
          }
      }
      //////////////////////////////////////////////////////// アイコンの管理 //
      
      
      
      // ユーザーグラフ ////////////////////////////////////////////////////////
      var graph_window_is_first_open = true;
      
      function open_graph(name, e) {
          
          (function reset_graph_window() {
              $("#usericon").attr('src', 'appimg.jpg');
              $("#username").html('loading..');
              $("#call-count").text(0);
              $("#callee-count").text(0);
              $("#call img").remove();
              $("#callee img").remove();
              
              if (graph_window_is_first_open && e) {
                  $("#user-graph")
                      .css('left', e.pageX + 10)
                      .css('top' , e.pageY - 120);
                  graph_window_is_first_open = false;
              }
              $("#user-graph").fadeIn(250);
          })();
          
          
          function lineup_icon(graph, type) {
              var elem = $('#' + type);
              
              for (var x_name in graph[type]) {
                  var value = graph[type][x_name];
                  var title = x_name + ' ' + value + '回';
                  var func = (function (name) {
                                  return function () {
                                      open_graph(name);
                                  };
                              })(x_name);
                  
                  var img = $(document.createElement('img'))
                      .attr('name' , x_name)
                      .attr('title', title)
                      .attr('src'  , 'appimg.jpg')
                      .click(func);
                  elem.append(img);
                  get_user_icons(x_name);
              }
          }
          
          
          // グラフの読み込み          
          var data = { name: name };
          $.get('/api/graph', data,
                function (result) {
                    if (! result) return;
                    var res = eval('(' + result + ')');
                    var profile_image_url = res['img'];
                    if (profile_image_url != 'null') {
                        $("#usericon").attr('src', profile_image_url);
                        user_icons[name] = profile_image_url;
                    }
                    var namelink = '<a href="http://twitter.com/' + name + '" target="twitter">@' + name + '</a>';
                    $("#username").html(namelink);
                    $("#call-count").text(res['call']);
                    $("#callee-count").text(res['callee']);
                    
                    lineup_icon(res['graph'], 'call');
                    lineup_icon(res['graph'], 'callee');
                });
      }
      
      function add_open_graph_function(a) {
          var name = a.text().substr(1);
          var func = (function (name) {
                          return function (e) { open_graph(name, e); };
                      })(name);
          a.get(0).onclick = func;
      }
      
      $("#graph-close button").click(
          function () {
              $("#user-graph").fadeOut(250);             
          });
      //////////////////////////////////////////////////////// ユーザーグラフ //
      
      
      
      // 履歴 //////////////////////////////////////////////////////////////////
      function tweet_user_link(name) {
          return '<a href="javascript:void(0);" type="user">@' + name + '</a>';
      }
      
      function tweet_status_link(user, status_id, datetime) {
          var caption = timeago(datetime * 1000);
          return '<i>(<a href="http://twitter.com/' + user + '/status/' + status_id + '" target="twitter" class="history-time" datetime="' + datetime + '">' + caption+ '</a>)</i>';
      }
      
      
      var min_id = null;
      var max_id = null;
      var reload_count = 0;
      function load_history(limit) {
          if (selected_tab != 'history') return;
          
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
          
          $.get('/api/history2', data,
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
                   
                   
                   function auto_reload_history() {
                       load_history(-20);
                   }
                   
                   if (limit < 0) {
                       if (list.length == 0) {
                           if (reload_count == 0) {
                               setTimeout(auto_reload_history, 5 * 1000);
                           } else if (reload_count < 5) {
                               setTimeout(auto_reload_history, 10 * 1000);
                           } else if (reload_count < 10) {
                               setTimeout(auto_reload_history, 30 * 1000);
                           } else if (reload_count < 20) {
                               setTimeout(auto_reload_history, 60 * 1000);
                           } else {
                               setTimeout(auto_reload_history, 120 * 1000);
                           }
                           reload_count++;
                       } else {
                           reload_count = 0;
                           if (res['n']) {
                               setTimeout(auto_reload_history,  1 * 1000);
                           } else {
                               setTimeout(auto_reload_history,  3 * 1000);
                           }
                       }
                   } else if (limit == 0) {
                       setTimeout(auto_reload_history, 10 * 1000);
                   }
                   
                   if (list.length != 0) {
                       $('#history-list a[type="user"]').each(
                           function () { add_open_graph_function($(this)); }
                       );
                   }
               });
      }
      
      
      $("#history-more-see").click(
          function () {
              $("#progress").show();
              load_history(20);
          });
      
      
      function timeago (time) {
  		  var diff = (new Date().getTime() - time) / 1000;
		  var day_diff = Math.floor(diff / 86400);
          
          if (day_diff == 0) {
              if (diff < 20) return '今';
              if (diff < 60) return Math.floor(diff) + '秒前';
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
      
      
      function refresh_time() {
          $(".history-time").each(
              function () {
                  var datetime = $(this).attr('datetime');
                  var now_text = $(this).text();
                  var new_text = timeago(datetime * 1000);
                  if (now_text != new_text) {
                      $(this).text(new_text);
                  } else {
                      if (now_text != '今') {
                          return false;
                      }
                  }
                  return true;
              });
      }
      ////////////////////////////////////////////////////////////////// 履歴 //
      
      
      
      // ランキング ////////////////////////////////////////////////////////////
      function lineup_ranking(type, data) {
          var elem = $('#ranking-' + type);
          for (var i = 0; i < data.length; i++) {
              var item = data[i];
              var name = item[0];
              var profile_image_url = item[1];
              var count = item[2];
              
              var img = $(document.createElement('img'));
              img.attr('src', profile_image_url);
              user_icons[name] = profile_image_url;

              var a = $(document.createElement('a'));
              a.text('@' + name).attr('href', 'javascript:void(0)');
              add_open_graph_function(a);
              
              var span = $(document.createElement('span'));
              span.text(count + '回');
              
              var li = $(document.createElement('li'));
              li.append(img);
              li.append(a);
              li.append(span);
              
              elem.append(li);
          }
      }
      
      
      function load_ranking(limit) {
          var data = { limit: limit };
          $.get('/api/ranking', data,
                function (result) {
                    var res = eval('(' + result + ')');
                    lineup_ranking('call'  , res['call']  );
                    lineup_ranking('callee', res['callee']);
                });
      }
      //////////////////////////////////////////////////////////// ランキング //
      
      
      
      // タブ //////////////////////////////////////////////////////////////////
      var alltab = [];
      var selected_tab = null;
      
      $("#navitab li").each(
          function () {
              var id = $(this).attr('id');
              alltab.push($(this));
              $(this).click(
                  function () {
                      for (var i = 0; i < alltab.length; i++) {
                          var xid = alltab[i].attr('id');
                          var tabname = xid.substr(4);
                          if (xid == id) {
                              alltab[i]
                                  .css('color', 'black')
                                  .css('background', 'white')
                                  .css('border-bottom-color', 'white');
                              $('#' + tabname).show();
                              selected_tab = tabname;
                          } else {
                              alltab[i]
                                  .css('color', 'gray')
                                  .css('background', 'lightgray')
                                  .css('border-bottom-color', 'darkgray');
                              $('#' + tabname).hide();
                          }
                      }
                  });
          });
      
      
      var history_load_is_first_time = true;
      $('#tab-history').click(
          function () {
              if (history_load_is_first_time) {
                  load_history();
                  history_load_is_first_time = false;
              } else {
                  load_history(-5);
              }

          });

      
      var ranking_is_loaded = false;
      $('#tab-ranking').click(
          function () {
              if (! ranking_is_loaded) {
                  load_ranking(10);                  
                  ranking_is_loaded = true;
              }
          });
      ////////////////////////////////////////////////////////////////// タブ //
      
      
      //
      $('#tab-history').click();
      $('#user-graph').draggable();
      setInterval(refresh_time, 10 * 1000);
});
