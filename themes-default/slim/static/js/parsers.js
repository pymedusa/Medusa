$.tablesorter.addParser({
    id: 'showNames',
    is() {
        return false;
    },
    format(s) {
        if (s.indexOf('Loading...') === 0) {
            return s.replace('Loading...', '000');
        }
        return (MEDUSA.config.sortArticle ? (s || '') : (s || '').replace(/^(The|A|An)\s/i, '')); // eslint-disable-line no-undef
    },
    type: 'text'
});
$.tablesorter.addParser({
    id: 'quality',
    is() {
        return false;
    },
    format(s) {
        const replacements = {
            custom: 11,
            bluray: 10, // Custom: Only bluray
            hd1080p: 9,
            '1080p': 8, // Custom: Only 1080p
            hdtv: 7, // Custom: 1080p and 720p (only HDTV)
            'web-dl': 6, // Custom: 1080p and 720p (only WEB-DL)
            hd720p: 5,
            '720p': 4, // Custom: Only 720p
            hd: 3,
            sd: 2,
            any: 1,
            best: 0
        };
        return replacements[s.toLowerCase()];
    },
    type: 'numeric'
});
$.tablesorter.addParser({
    id: 'realISODate',
    is() {
        return false;
    },
    format(s) {
        return new Date(s).getTime();
    },
    type: 'numeric'
});

$.tablesorter.addParser({
    id: 'cDate',
    is() {
        return false;
    },
    format(s) {
        return s;
    },
    type: 'numeric'
});
$.tablesorter.addParser({
    id: 'eps',
    is() {
        return false;
    },
    format(s) {
        const match = s.match(/^(.*)/);

        if (match === null || match[1] === '?') {
            return -10;
        }

        const nums = match[1].split(' / ');
        if (nums[0].indexOf('+') !== -1) {
            const numParts = nums[0].split('+');
            nums[0] = numParts[0];
        }

        nums[0] = parseInt(nums[0], 10);
        nums[1] = parseInt(nums[1], 10);

        if (nums[0] === 0) {
            return nums[1];
        }
        let finalNum = parseInt(($('meta[data-var="max_download_count"]').data('content')) * nums[0] / nums[1], 10);
        const pct = Math.round((nums[0] / nums[1]) * 100) / 1000;
        if (finalNum > 0) {
            finalNum += nums[0];
        }

        return finalNum + pct;
    },
    type: 'numeric'
});
