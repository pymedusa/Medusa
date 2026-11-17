import { VueGoodTable } from 'vue-good-table';
import PaginatedTable from './paginated-table';

// Season headings are presentation rows, not episodes in the pagination count.
export default {
    extends: PaginatedTable,
    computed: {
        paginated() {
            if (!this.groupOptions.enabled || this.mode === 'remote' || !this.paginate || this.currentPerPage === -1) {
                return VueGoodTable.computed.paginated.call(this);
            }

            const total = this.processedRows.reduce((count, group) => count + group.children.length, 0);
            let start = (this.currentPage - 1) * this.currentPerPage;
            if (this.currentPage > 1 && start >= total) {
                this.changePage(1);
                start = 0;
            }
            const end = start + this.currentPerPage;
            const result = [];
            let offset = 0;
            for (const group of this.processedRows) {
                const nextOffset = offset + group.children.length;
                if (nextOffset > start && offset < end) {
                    const shell = {
                        ...group,
                        children: group.children.slice(Math.max(0, start - offset), end - offset)
                    };
                    this.handleExpanded(shell);
                    result.push(shell);
                }
                offset = nextOffset;
                if (offset >= end) {
                    break;
                }
            }
            return result;
        }
    }
};
