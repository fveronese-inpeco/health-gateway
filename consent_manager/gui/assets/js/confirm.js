// Copyright (c) 2017-2018 CRS4
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of
// this software and associated documentation files (the "Software"), to deal in
// the Software without restriction, including without limitation the rights to use,
// copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
// and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all copies or
// substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
// INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
// AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import React from 'react';
import 'url-search-params-polyfill';
import DataProvider from './dataProvider';
import {ConfirmConsents} from './consent';
import NotificationManager from './notificationManager';

class Confirm extends React.Component {

    renderConsents(data) {
        const params = new URLSearchParams(this.props.location.search);
        const callbackUrl = params.get('callback_url');
        return (
            <ConfirmConsents data={data}
                             notifier={this.notifier}
                             callbackUrl={callbackUrl}/>
        )
    }

    componentDidMount() {
        this.notifier = this.refs.notificationManager;
    }

    render() {
        const params = new URLSearchParams(this.props.location.search);
        const confirmId = params.getAll('confirm_id');
        return (
            <div>
                <DataProvider endpoint={'/v1/consents/find/'}
                              params={{'confirm_id': confirmId}}
                              render={data => this.renderConsents(data)}/>
                <NotificationManager ref="notificationManager"/>
            </div>
        )
    }
}

export default Confirm;