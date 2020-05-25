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
