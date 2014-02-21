var tag = document.createElement('script'),
  first_script_tag,
  player;

tag.src = "http://www.youtube.com/iframe_api";
first_script_tag = document.getElementsByTagName('script')[0];
first_script_tag.parentNode.insertBefore(tag, first_script_tag);

// My YouTube API methods
function onYTError(event)
{
  $('.errors').html(
    $('.errors').html() +
    '<div class="alert alert-danger">' +
      '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
      '<strong>Error!</strong> Having difficulty connecting to the YouTube API. The player controls will still work, but certain functions will not. This is most likely due to network problems. Thanks for your patience!' +
    '</div>'
  );
}

function onPlayerReady() // removed event param for now, not used
{
  player.playVideoAt(0);
}

function updateNowPlaying()
{
  if(player)
  {
    var currentlyPlayingIndex = player.getPlaylistIndex(),
      nowPlaying = $('.track.nowPlaying'),
      currentlyPlayingTrackRow = $('.track[data-playnum = \'' + currentlyPlayingIndex + '\']');

    nowPlaying.removeClass('nowPlaying');
    currentlyPlayingTrackRow.addClass('nowPlaying');

    document.title = 'flock - ' + currentlyPlayingTrackRow.find('.playTitle').html();
  }
}

function onPlayerStateChange() // removed event param for now, not used
{
  updateNowPlaying();
}

function onYouTubeIframeAPIReady() {
  player = new YT.Player('player', {
    events: {
    'onError': onYTError,
    'onReady': onPlayerReady,
    'onStateChange': onPlayerStateChange
    }
  });
}

function getParameterByName(name) {
  var match = new RegExp('[?&]' + name + '=([^&]*)').exec(window.location.search);
  return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
}

function addArg(key, value)
{
  var newParams = '';
  for(var i = 0; i < key.length; i ++)
  {
    newParams += '&' + key[i] + '=' + value[i];
  }

  window.location.search = '?subreddits=' + getParameterByName('subreddits') + newParams;
}

$(document).ready(function() {
  $('.playTrack').on('click', function() {
    player.playVideoAt($(this).parent().data('playnum'));
    updateNowPlaying();
  });

  $('.commentNum').on('click', function(e) {
    e.stopPropagation();
  });

  $('.chosen-select').chosen(
    {
      no_results_text: "Oops, that one's too hip for us - add it to your search with space or enter", search_contains: true}
  ).change(
    function(event, params) {
      var subreddits = $('#subredditsParam').val();

      if(params.selected)
      {
        subreddits += ' ' + params.selected;
      }
      if(params.deselected)
      {
        subreddits = subreddits.replace(params.deselected, '');
        subreddits = subreddits.replace('  ', ' ');
      }

      if(subreddits[0] === ' ')
      {
        subreddits = subreddits.slice(1);
      }
      if(subreddits[subreddits.length - 1] === ' ')
      {
        subreddits = subreddits.slice(0, subreddits.length - 2);
      }

      $('#subredditsParam').val(subreddits);
    }).css('height', '34');
});