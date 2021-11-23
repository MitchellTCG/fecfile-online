import { OnInit, Directive } from '@angular/core';

// TODO: Abstract all common functionality
@Directive()
export class AbstractLogin implements OnInit {
    public show: boolean = false;

    showPassword() {
        this.show = !this.show;
    }

    ngOnInit(): void {
    }
}
