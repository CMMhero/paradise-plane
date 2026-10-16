import type { TDropdownProps } from "../types";

export type MemberDropdownProps = TDropdownProps & {
  button?: React.ReactNode;
  dropdownArrow?: boolean;
  dropdownArrowClassName?: string;
  placeholder?: string;
  tooltipContent?: string;
  onClose?: () => void;
  showUserDetails?: boolean;
  /**
   * "hanya diri sendiri": opsi dropdown disaring ke satu id ini saja.
   * Dipakai layar buat/ubah work item saat pembukanya staf — server tetap
   * pemegang keputusan (gerbang hierarki), ini cuma supaya daftarnya tidak
   * menampilkan orang yang pasti ditolak.
   */
  hanyaDiriSendiri?: string | null;
} & (
    | {
        multiple: false;
        onChange: (val: string | null) => void;
        value: string | null;
      }
    | {
        multiple: true;
        onChange: (val: string[]) => void;
        value: string[];
      }
  );
