/**
 * Attach a jquery qtip to elements with the .imdbstars class.
 */
export const attachImdbTooltip = () => {
    $('.imdbstars').qtip({
        content: {
            text() {
                // Retrieve content from custom attribute of the $('.selector') elements.
                return $(this).attr('qtip-content');
            }
        },
        show: {
            solo: true
        },
        position: {
            my: 'right center',
            at: 'center left',
            adjust: {
                y: 0,
                x: -6
            }
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
        }
    });
};

/**
 * Attach a default qtip to elements with the addQTip class.
 */
export const addQTip = () => {
    $('.addQTip').each((_, element) => {
        $(element).css({
            cursor: 'help',
            'text-shadow': '0px 0px 0.5px #666'
        });

        const my = $(element).data('qtip-my') || 'left center';
        const at = $(element).data('qtip-at') || 'middle right';

        $(element).qtip({
            show: {
                solo: true
            },
            position: {
                my,
                at
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
            }
        });
    });
};
