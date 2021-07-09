/**
 * Vue Cookie handler for the vue-good-tables enable/disable columns feature.
 * @param {String} cookiePrefix String used to specify the specific table.
 * @example - Prefix `Home` with the column Label `title` will result in the cookie key `Home-title`
 * @returns {void}
 */
export const manageCookieMixin = cookiePrefix => {
    return {
        methods: {
            getCookie(key) {
                if (key.includes(cookiePrefix)) {
                    return JSON.parse(key);
                }
                return JSON.parse(this.$cookies.get(`${cookiePrefix}-${key}`));
            },
            setCookie(key, value) {
                return this.$cookies.set(`${cookiePrefix}-${key}`, JSON.stringify(value));
            },
            /**
             * Save vue-good-table sort field and sort order (desc/asc)
             * @param {*} evt - Vue good table sorting event (triggered by the `on-sort-change` event)
             */
            saveSorting(evt) {
                const { setCookie } = this;
                // Store cookies, for sort field and type (asc/desc)
                setCookie('sort-field', evt.map(item => item.field));
                setCookie('sort-type', evt.map(item => item.type));
            },
            /**
             * Get vue-good-table sort field and sort order.
             * @param {string} defaultField - default vue good table field to sort by.
             * @param {string} defaultType - default vue good table sort order (ascending / descending).
             * @returns {object} - Object with the field and type properties.
             */
            getSortBy(defaultField = 'title', defaultType = 'asc') {
                const { getCookie } = this;
                // Try to get cookies, for sort field and type (asc/desc)
                const sortField = getCookie('sort-field');
                const sortType = getCookie('sort-type');
                const sort = [];

                if (Array.isArray(sortField) && sortField.length === 2) {
                    sortField.forEach((_, index) => {
                        sort.push({ field: sortField[index] || defaultField, type: sortType[index] || defaultType });
                    });
                    return sort;
                }

                if (sortField === null || sortType === null) {
                    return ({ field: defaultField, type: defaultType });
                }

                return ({ field: sortField[0] || defaultField, type: sortType[0] || defaultType });
            }
        },
        created() {
            // Watch the columns property on the VM. This is the default named property for the vue-good-tables columns.
            this.$watch(() => this.columns, columns => {
                // Monitor the columns, to update the cookies, when changed.
                const { setCookie } = this;
                for (const column of columns) {
                    if (column) {
                        setCookie(column.label, column.hidden);
                    }
                }
            }, { deep: true });
        }
    };
};
