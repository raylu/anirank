window.addEvent('domready', function() {
	'use strict';

	$$('h2 a').addEvent('click', function(e) {
		e.preventDefault();
		var id = e.target.get('text');
		var animelist = $(id);
		if (animelist.getStyle('display') == 'none')
			animelist.setStyle('display', 'block')
		else
			animelist.setStyle('display', 'none')
	});
});
