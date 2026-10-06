# iiko: есть ли автор операции

## OLAP · TRANSACTIONS
всего полей: **116**

### похоже на автора — 7 шт.
| поле | название | тип | агрегируемое |
|---|---|---|---|
| `Product.Tags.IdsCombo` | ID пользовательских свойств (комб.) | STRING | False |
| `Product.Tag.Id` | ID пользовательского свойства | ID | False |
| `Contr-Product.Tags.IdsCombo` | Корр.ID пользовательских свойств (комб.) | STRING | False |
| `Contr-Product.Tags.NamesCombo` | Корр.Пользовательские свойства (комб.) | STRING | False |
| `Product.Tags.NamesCombo` | Пользовательские свойства (комб.) | STRING | False |
| `Product.Tag.Name` | Пользовательское свойство | STRING | False |
| `Department.JurPerson` | Юридическое лицо | STRING | False |

<details><summary>все поля</summary>

| поле | название | тип |
|---|---|---|
| `Account.AccountHierarchyFull` | Иерархия счета | STRING |
| `Account.AccountHierarchySecond` | Счет 2-го уровня | STRING |
| `Account.AccountHierarchyThird` | Счет 3-го уровня | STRING |
| `Account.AccountHierarchyTop` | Счет 1-го уровня | STRING |
| `Account.Code` | Код счета | STRING |
| `Account.CounteragentType` | Тип контрагента | ENUM |
| `Account.Group` | Группа счета | ENUM |
| `Account.Id` | ID счета | ID_STRING |
| `Account.IsCashFlowAccount` | Участвует ли счет в ДДС | ENUM |
| `Account.Name` | Счет | STRING |
| `Account.StoreOrAccount` | Склад/счет | ENUM |
| `Account.Type` | Тип счета | ENUM |
| `Amount` | Количество | AMOUNT |
| `Amount.In` | Приход (кол-во) | AMOUNT |
| `Amount.Out` | Расход (кол-во) | AMOUNT |
| `Amount.StoreInOutTyped` | Оборот эл.номенклатуры | AMOUNT |
| `CashFlowCategory` | Статья ДДС | STRING |
| `CashFlowCategory.Hierarchy` | Иерархия статей ДДС | STRING |
| `CashFlowCategory.HierarchyLevel1` | Статья ДДС 1-го уровня | STRING |
| `CashFlowCategory.HierarchyLevel2` | Статья ДДС 2-го уровня | STRING |
| `CashFlowCategory.HierarchyLevel3` | Статья ДДС 3-го уровня | STRING |
| `CashFlowCategory.Type` | Тип статьи ДДС | ENUM |
| `Comment` | Комментарий | STRING |
| `Conception` | Концепция | STRING |
| `Conception.Code` | Код концепции | STRING |
| `Contr-Account.Code` | Код корр.счета | STRING |
| `Contr-Account.Group` | Группа корр.счета | ENUM |
| `Contr-Account.Name` | Корр.Счет/Склад | STRING |
| `Contr-Account.Type` | Тип корр.счета | ENUM |
| `Contr-Amount` | Корр.количество | AMOUNT |
| `Contr-Product.AccountingCategory` | Корр.Бухгалтерская категория | STRING |
| `Contr-Product.AlcoholClass` | Класс алкогольной продукции | STRING |
| `Contr-Product.AlcoholClass.Code` | Код класса алкогольной продукции | STRING |
| `Contr-Product.AlcoholClass.Group` | Группа алкогольной продукции | STRING |
| `Contr-Product.AlcoholClass.Type` | Тип алкогольной продукции | ENUM |
| `Contr-Product.Category` | Корр.Категория номенклатуры | STRING |
| `Contr-Product.Category.Id` | Корр.ID категории номенклатуры | ID_STRING |
| `Contr-Product.CookingPlaceType` | Корр.Тип места приготовления | STRING |
| `Contr-Product.Hierarchy` | Корр.Иерархия номенклатуры | STRING |
| `Contr-Product.Id` | Корр.ID эл.номенклатуры | ID_STRING |
| `Contr-Product.MeasureUnit` | Корр.Единица измерения | STRING |
| `Contr-Product.Name` | Корр.Элемент номенклатуры | STRING |
| `Contr-Product.Num` | Корр.Артикул элемента номенклатуры | STRING |
| `Contr-Product.SecondParent` | Корр.Группа номенклатуры 2-го уровня | STRING |
| `Contr-Product.Tags.IdsCombo` | Корр.ID пользовательских свойств (комб.) | STRING |
| `Contr-Product.Tags.NamesCombo` | Корр.Пользовательские свойства (комб.) | STRING |
| `Contr-Product.ThirdParent` | Корр.Группа номенклатуры 3-го уровня | STRING |
| `Contr-Product.TopParent` | Корр.Группа номенклатуры 1-го уровня | STRING |
| `Contr-Product.Type` | Корр.Тип элемента номенклатуры | ENUM |
| `Counteragent.Id` | ID контрагента | ID_STRING |
| `Counteragent.Name` | Контрагент | STRING |
| `DateSecondary.DateTimeTyped` | Дата и время проводки | DATETIME |
| `DateSecondary.DateTyped` | Дата проводки | DATE |
| `DateTime.DateTyped` | Учетный день | DATE |
| `DateTime.DayOfWeak` | День недели | STRING |
| `DateTime.Hour` | Час | STRING |
| `DateTime.Month` | Месяц | STRING |
| `DateTime.Quarter` | Квартал | STRING |
| `DateTime.Typed` | Дата и время | DATETIME |
| `DateTime.WeekInMonth` | Неделя месяца | STRING |
| `DateTime.WeekInYear` | Неделя года | STRING |
| `DateTime.Year` | Год | STRING |
| `Department` | Торговое предприятие | STRING |
| `Department.Category1` | Категория 1 | STRING |
| `Department.Category2` | Категория 2 | STRING |
| `Department.Category3` | Категория 3 | STRING |
| `Department.Category4` | Категория 4 | STRING |
| `Department.Category5` | Категория 5 | STRING |
| `Department.Code` | Код подразделения | STRING |
| `Department.JurPerson` | Юридическое лицо | STRING |
| `Document` | Номер документа | STRING |
| `FinalBalance.Amount` | Конечный остаток товара | AMOUNT |
| `FinalBalance.Money` | Конечный денежный остаток | MONEY |
| `OrderId` | ID заказа | ID |
| `OrderNum` | Номер заказа | STRING |
| `PercentOfSummary.ByCol` | % по столбцу | PERCENT |
| `PercentOfSummary.ByRow` | % по строке | PERCENT |
| `Product.AccountingCategory` | Бухгалтерская категория | STRING |
| `Product.AlcoholClass` | Класс алкогольной продукции | STRING |
| `Product.AlcoholClass.Code` | Код класса алкогольной продукции | STRING |
| `Product.AlcoholClass.Group` | Группа алкогольной продукции | STRING |
| `Product.AlcoholClass.Type` | Тип алкогольной продукции | ENUM |
| `Product.AvgSum` | Средняя цена | MONEY |
| `Product.Category` | Категория номенклатуры | STRING |
| `Product.Category.Id` | ID категории номенклатуры | ID_STRING |
| `Product.CookingPlaceType` | Тип места приготовления | STRING |
| `Product.Hierarchy` | Иерархия номенклатуры | STRING |
| `Product.Id` | ID элемента номенклатуры | ID_STRING |
| `Product.MeasureUnit` | Единица измерения | STRING |
| `Product.Name` | Элемент номенклатуры | STRING |
| `Product.Num` | Артикул элемента номенклатуры | STRING |
| `Product.SecondParent` | Группа номенклатуры 2-го уровня | STRING |
| `Product.Tag.Id` | ID пользовательского свойства | ID |
| `Product.Tag.Name` | Пользовательское свойство | STRING |
| `Product.Tags.IdsCombo` | ID пользовательских свойств (комб.) | STRING |
| `Product.Tags.NamesCombo` | Пользовательские свойства (комб.) | STRING |
| `Product.ThirdParent` | Группа номенклатуры 3-го уровня | STRING |
| `Product.TopParent` | Группа номенклатуры 1-го уровня | STRING |
| `Product.Type` | Тип элемента номенклатуры | ENUM |
| `Session.CashRegister` | Касса | STRING |
| `Session.Group` | Группа | STRING |
| `Session.GroupId` | ID группы | ID_STRING |
| `Session.RestaurantSection` | Отделение | STRING |
| `StartBalance.Amount` | Начальный остаток товара | AMOUNT |
| `StartBalance.Money` | Начальный денежный остаток | MONEY |
| `Store` | Склад | STRING |
| `Sum.Incoming` | Сумма прихода | MONEY |
| `Sum.Outgoing` | Сумма расхода | MONEY |
| `Sum.PartOfIncome` | % от выручки | PERCENT |
| `Sum.PartOfSummaryByCol` | % суммы от итога по столбцам | PERCENT |
| `Sum.PartOfSummaryByRow` | % суммы от итога по строкам | PERCENT |
| `Sum.PartOfTotalIncome` | % от общей выручки | PERCENT |
| `Sum.ResignedSum` | Сумма | MONEY |
| `TransactionSide` | Дебет/Кредит | ENUM |
| `TransactionType` | Тип транзакции | ENUM |
| `TransactionType.Code` | Код транзакции | OBJECT |

</details>

## OLAP · SALES
всего полей: **285**

### похоже на автора — 12 шт.
| поле | название | тип | агрегируемое |
|---|---|---|---|
| `AuthUser.Id` | ID авторизовавшего | ID_STRING | False |
| `DishTags.IdsCombo` | ID пользовательских свойств (комб.) | STRING | False |
| `DishTag.Id` | ID пользовательского свойства | ID | False |
| `AuthUser` | Авторизовал | STRING | False |
| `CreditUser` | В кредит на... | STRING | False |
| `Delivery.CustomerCreatedDateTyped` | Дата создания клиента | DATE | False |
| `Card` | Карта авторизации | STRING | False |
| `CreditUser.Company` | Компания-контрагент | STRING | False |
| `DishTags.NamesCombo` | Пользовательские свойства (комб.) | STRING | False |
| `DishTag.Name` | Пользовательское свойство | STRING | False |
| `WriteoffUser` | Списано на сотрудника | STRING | False |
| `PriceCategoryUserCardOwner` | ЦК контрагент | STRING | False |

<details><summary>все поля</summary>

| поле | название | тип |
|---|---|---|
| `AuthUser` | Авторизовал | STRING |
| `AuthUser.Id` | ID авторизовавшего | ID_STRING |
| `Banquet` | Банкет | ENUM |
| `Bonus.CardNumber` | Номер бонусной карты | STRING |
| `Bonus.Sum` | Сумма бонуса | MONEY |
| `Bonus.Type` | Тип бонуса | STRING |
| `Card` | Карта авторизации | STRING |
| `CardNumber` | Номер карты оплаты | STRING |
| `CardOwner` | Владелец карты гостя | STRING |
| `CardType` | Кредитная карта | STRING |
| `CardTypeName` | Тип карты | STRING |
| `CashLocation` | Расположение кассы | STRING |
| `CashRegisterName` | Касса | STRING |
| `CashRegisterName.CashRegisterSerialNumber` | Серийный номер ФР | STRING |
| `CashRegisterName.Number` | Номер кассы | INTEGER |
| `Cashier` | Кассир | STRING |
| `Cashier.Code` | Табельный номер кассира | STRING |
| `Cashier.Id` | ID кассира | ID_STRING |
| `CloseTime` | Время закрытия | DATETIME |
| `CloseTime.Minutes15` | 15-минутный интервал закрытия | STRING |
| `Comment` | Комментарий к блюду | STRING |
| `Conception` | Концепция | STRING |
| `Conception.Code` | Код концепции | STRING |
| `Cooking.Cooking1Duration.Avg` | Продолжительность приготовления 1 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking2Duration.Avg` | Продолжительность приготовления 2 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking3Duration.Avg` | Продолжительность приготовления 3 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking4Duration.Avg` | Продолжительность приготовления 4 (средняя) | DURATION_IN_SECONDS |
| `Cooking.CookingDuration.Avg` | Продолжительность приготовления (средняя) | DURATION_IN_SECONDS |
| `Cooking.CookingLateTime.Avg` | Опоздание приготовления (средняя) | DURATION_IN_SECONDS |
| `Cooking.FeedLateTime.Avg` | Опоздание подачи (средняя) | DURATION_IN_SECONDS |
| `Cooking.GuestWaitTime.Avg` | Продолжительность ожидания гостя (средняя) | DURATION_IN_SECONDS |
| `Cooking.KitchenTime.Avg` | Продолжительность работы кухни (средняя) | DURATION_IN_SECONDS |
| `Cooking.PublicExternalData` | Публичные данные плагинов о приготовлении | STRING |
| `Cooking.PublicExternalData.Xml` | Публичные данные плагинов о приготовлении (XML) | STRING |
| `Cooking.ServeNumber` | Номер подачи | STRING |
| `Cooking.ServeTime.Avg` | Продолжительность подачи гостю (средняя) | DURATION_IN_SECONDS |
| `Cooking.StartDelayTime.Avg` | Задержка начала приготовления (средняя) | DURATION_IN_SECONDS |
| `CookingPlace` | Место приготовления | STRING |
| `CookingPlace.Id` | ID места приготовления | ID_STRING |
| `CookingPlaceType` | Тип места приготовления | STRING |
| `Counteragent.Name` | Контрагент | STRING |
| `CouponInfo.Number` | Номер купона | STRING |
| `CouponInfo.Series` | Серия купона | STRING |
| `CouponInfos` | Серии и номера купонов | STRING |
| `CreditUser` | В кредит на... | STRING |
| `CreditUser.Company` | Компания-контрагент | STRING |
| `Currencies.Currency` | Валюта оплаты | STRING |
| `Currencies.CurrencyRate` | Курс валюты оплаты | MONEY |
| `Currencies.SumInCurrency` | Сумма в валюте оплаты / заказ | OBJECT |
| `DayOfWeekOpen` | День недели | STRING |
| `DeletedWithWriteoff` | Блюдо удалено | ENUM |
| `DeletionComment` | Комментарий к удалению блюда | STRING |
| `Delivery.ActualTime` | Фактическое время доставки | DATETIME |
| `Delivery.Address` | Адрес | STRING |
| `Delivery.AggregatedAvgCourierMark` | Средняя оценка курьера, % | AMOUNT |
| `Delivery.AggregatedAvgFoodMark` | Средняя оценка кухни, % | AMOUNT |
| `Delivery.AggregatedAvgMark` | Средняя оценка доставки, % | AMOUNT |
| `Delivery.AggregatedAvgOperatorMark` | Средняя оценка оператора, % | AMOUNT |
| `Delivery.AvgCourierMark` | Оценка курьера, % | AMOUNT |
| `Delivery.AvgFoodMark` | Оценка кухни, % | AMOUNT |
| `Delivery.AvgMark` | Оценка доставки, % | AMOUNT |
| `Delivery.AvgOperatorMark` | Оценка оператора, % | AMOUNT |
| `Delivery.BillTime` | Время печати накладной | DATETIME |
| `Delivery.CancelCause` | Причина отмены доставки | STRING |
| `Delivery.CancelComment` | Комментарий к отмене доставки | STRING |
| `Delivery.City` | Город | STRING |
| `Delivery.CloseTime` | Время закрытия доставки | DATETIME |
| `Delivery.ConfirmTime` | Время подтверждения доставки | DATETIME |
| `Delivery.CookingFinishTime` | Время окончания приготовления | DATETIME |
| `Delivery.CookingToSendDuration` | Длит: посл.серв.печать-отправка | INTEGER |
| `Delivery.Courier` | Курьер | STRING |
| `Delivery.Courier.Id` | ID курьера | STRING |
| `Delivery.CustomerCardNumber` | Номер карты клиента | STRING |
| `Delivery.CustomerCardType` | Тип карты клиента | STRING |
| `Delivery.CustomerComment` | Комментарий к клиенту | STRING |
| `Delivery.CustomerCreatedDateTyped` | Дата создания клиента | DATE |
| `Delivery.CustomerMarketingSource` | Реклама клиента | STRING |
| `Delivery.CustomerName` | ФИО клиента | STRING |
| `Delivery.CustomerOpinionComment` | Отзыв клиента | STRING |
| `Delivery.CustomerPhone` | Телефон клиента | STRING |
| `Delivery.Delay` | Опоздание доставки(мин) | INTEGER |
| `Delivery.DelayAvg` | Ср.опоздание доставки(мин) | AMOUNT |
| `Delivery.DeliveryComment` | Комментарий к доставке | STRING |
| `Delivery.DeliveryOperator` | Оператор доставки | STRING |
| `Delivery.DeliveryOperator.Id` | ID оператора доставки | STRING |
| `Delivery.DiffBetweenActualDeliveryTimeAndPredictedDeliveryTime` | Отклонение от сроков доставки, фактическое от прогнозируемог | INTEGER |
| `Delivery.EcsService` | Курьерская служба | STRING |
| `Delivery.Email` | e-mail доставки | STRING |
| `Delivery.ExpectedTime` | Планируемое время доставки | DATETIME |
| `Delivery.ExternalCartographyId` | Идентификатор адреса | STRING |
| `Delivery.Id` | ID доставки | ID |
| `Delivery.Index` | Индекс адреса | STRING |
| `Delivery.IsAsap` | Как можно скорее | ENUM |
| `Delivery.IsDelivery` | Доставка | ENUM |
| `Delivery.Line1` | Куда везти | STRING |
| `Delivery.Line2` | Детали адреса | STRING |
| `Delivery.MarketingSource` | Реклама | STRING |
| `Delivery.Number` | Номер доставки | INTEGER |
| `Delivery.PackedTime` | Время окончания сборки доставки | DATETIME |
| `Delivery.Phone` | Телефон доставки | STRING |
| `Delivery.PredictedCookingCompleteTime` | Прогнозируемое время окончания готовки заказа | DATETIME |
| `Delivery.PredictedDeliveryTime` | Прогнозируемое время доставки | DATETIME |
| `Delivery.PrintTime` | Время печати доставки | DATETIME |
| `Delivery.Region` | Район | STRING |
| `Delivery.SendTime` | Время отправки доставки | DATETIME |
| `Delivery.ServiceType` | Тип доставки | ENUM |
| `Delivery.SourceKey` | Источник доставки | STRING |
| `Delivery.Street` | Улица | STRING |
| `Delivery.WayDuration` | Время в пути(мин) | INTEGER |
| `Delivery.WayDurationAvg` | Ср.время в пути(мин) | AMOUNT |
| `Delivery.WayDurationSum` | Сумм.время в пути(мин) | INTEGER |
| `Delivery.Zone` | Зона доставки | STRING |
| `Department` | Торговое предприятие | STRING |
| `Department.Category1` | Категория 1 | STRING |
| `Department.Category2` | Категория 2 | STRING |
| `Department.Category3` | Категория 3 | STRING |
| `Department.Category4` | Категория 4 | STRING |
| `Department.Category5` | Категория 5 | STRING |
| `Department.Code` | Код подразделения | STRING |
| `Department.Id` | ID подразделения | ID_STRING |
| `DiscountPercent` | Процент скидки | PERCENT |
| `DiscountSum` | Сумма скидки | MONEY |
| `DishAmountInt` | Количество блюд | AMOUNT |
| `DishAmountInt.PerOrder` | Ср. количество блюд на чек | AMOUNT |
| `DishCategory` | Категория блюда | STRING |
| `DishCategory.Accounting` | Бухгалтерская категория блюда | STRING |
| `DishCategory.Accounting.Id` | ID бухгалтерской категории блюда | ID |
| `DishCategory.Id` | ID категории блюда | ID_STRING |
| `DishCode` | Код блюда | STRING |
| `DishCode.Quick` | Код быстрого набора блюда | STRING |
| `DishDiscountSumInt` | Сумма со скидкой | MONEY |
| `DishDiscountSumInt.average` | Средняя сумма заказа | MONEY |
| `DishDiscountSumInt.averageByGuest` | Средняя выручка с гостя | MONEY |
| `DishDiscountSumInt.averagePrice` | Средняя цена без НДС | MONEY |
| `DishDiscountSumInt.averagePriceWithVAT` | Средняя цена | MONEY |
| `DishDiscountSumInt.averageWithoutVAT` | Средняя сумма заказа без НДС | MONEY |
| `DishDiscountSumInt.withoutVAT` | Сумма со скидкой без НДС | MONEY |
| `DishForeignName` | Наименование блюда на иностранном языке | STRING |
| `DishFullName` | Полное наименование блюда | STRING |
| `DishGroup` | Группа блюда | STRING |
| `DishGroup.Hierarchy` | Иерархия блюда | STRING |
| `DishGroup.Id` | ID группы блюда | ID |
| `DishGroup.Num` | Код группы блюда | STRING |
| `DishGroup.SecondParent` | Группа блюда 2-го уровня | STRING |
| `DishGroup.ThirdParent` | Группа блюда 3-го уровня | STRING |
| `DishGroup.TopParent` | Группа блюда 1-го уровня | STRING |
| `DishId` | ID блюда | ID_STRING |
| `DishMeasureUnit` | Единица измерения | STRING |
| `DishName` | Блюдо | STRING |
| `DishReturnSum` | Сумма возврата | MONEY |
| `DishReturnSum.withoutVAT` | Сумма возврата без НДС | MONEY |
| `DishServicePrintTime` | Сервисная печать блюда | DATETIME |
| `DishServicePrintTime.Max` | Сервисная печать последнего блюда | DATETIME |
| `DishServicePrintTime.OpenToLastPrintDuration` | Длит: откр.-посл.серв.печать | INTEGER |
| `DishSize.Id` | ID размера блюда | ID_STRING |
| `DishSize.Name` | Размер блюда | STRING |
| `DishSize.Priority` | Порядковый номер размера блюда | INTEGER |
| `DishSize.Scale.Id` | ID шкалы размеров блюда | ID |
| `DishSize.Scale.Name` | Шкала размеров блюда | STRING |
| `DishSize.ShortName` | Код размера блюда | STRING |
| `DishSumInt` | Сумма без скидки | MONEY |
| `DishSumInt.averagePriceWithVAT` | Средняя цена без скидки | MONEY |
| `DishTag.Id` | ID пользовательского свойства | ID |
| `DishTag.Name` | Пользовательское свойство | STRING |
| `DishTags.IdsCombo` | ID пользовательских свойств (комб.) | STRING |
| `DishTags.NamesCombo` | Пользовательские свойства (комб.) | STRING |
| `DishTaxCategory.Id` | ID налоговой категории | ID |
| `DishTaxCategory.Name` | Налоговая категория | STRING |
| `DishType` | Тип товара | ENUM |
| `ExternalNumber` | Внешний номер заказа | STRING |
| `FiscalChequeNumber` | Номера фиск. чеков | STRING |
| `GroupOrderId` | ID группового заказа | ID |
| `GroupOrderNum` | Номер группового чека | INTEGER |
| `GuestNum` | Количество гостей | AMOUNT |
| `GuestNum.Avg` | Ср.кол-во гостей на чек | AMOUNT |
| `HourClose` | Час закрытия | STRING |
| `HourOpen` | Час открытия | STRING |
| `IncentiveSumBase.Sum` | Мотивационный бонус | MONEY |
| `IncreasePercent` | Процент надбавки | PERCENT |
| `IncreaseSum` | Сумма надбавки | MONEY |
| `ItemSaleEvent.Id` | ID позиции заказа | ID |
| `ItemSaleEventDiscountType` | Наименование скидки, надбавки | STRING |
| `ItemSaleEventDiscountType.ComboAmount` | Количество Комбо | INTEGER |
| `ItemSaleEventDiscountType.ComboGroupId` | ID Шага Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboGroupName` | Шаг Комбо | STRING |
| `ItemSaleEventDiscountType.ComboId` | ID Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboName` | Название Комбо | STRING |
| `ItemSaleEventDiscountType.ComboSizeId` | ID размера Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboSizeName` | Размер Комбо | STRING |
| `ItemSaleEventDiscountType.DiscountAmount` | Колич. блюд со скидкой | AMOUNT |
| `JurName` | Юридическое лицо | STRING |
| `LocalTax1.Sum` | Местный налог 1 | MONEY |
| `LocalTax2.Sum` | Местный налог 2 | MONEY |
| `LocalTax3.Sum` | Местный налог 3 | MONEY |
| `LocalTax4.Sum` | Местный налог 4 | MONEY |
| `LocalTax5.Sum` | Местный налог 5 | MONEY |
| `Mounth` | Месяц | STRING |
| `NonCashPaymentType` | Безналичный тип оплаты | STRING |
| `NonCashPaymentType.DocumentType` | Тип документа списания | ENUM |
| `OpenDate.Typed` | Учетный день | DATE |
| `OpenTime` | Время открытия | DATETIME |
| `OpenTime.Minutes15` | 15-минутный интервал открытия | STRING |
| `OperationType` | Операция | ENUM |
| `OrderComment` | Комментарий заказа | STRING |
| `OrderDeleted` | Заказ удален | ENUM |
| `OrderDiscount.GuestCard` | Гостевая карта | STRING |
| `OrderDiscount.Type` | Тип скидки | STRING |
| `OrderDiscount.Type.IDs` | ID типов скидок | STRING |
| `OrderIncrease.Type` | Тип надбавки | STRING |
| `OrderIncrease.Type.IDs` | ID типов надбавок | STRING |
| `OrderItems` | Позиций чека | INTEGER |
| `OrderNum` | Номер чека | INTEGER |
| `OrderServiceType` | Режим обслуживания | ENUM |
| `OrderTime.AverageOrderTime` | Ср.время обсл.(мин) | AMOUNT |
| `OrderTime.AveragePrechequeTime` | Ср.время в пречеке (мин) | AMOUNT |
| `OrderTime.OrderLength` | Время обслуживания (мин) | INTEGER |
| `OrderTime.OrderLengthSum` | Время обсл.сумм.(мин) | INTEGER |
| `OrderTime.PrechequeLength` | Время в пречеке (мин) | INTEGER |
| `OrderType` | Тип заказа | STRING |
| `OrderType.Id` | ID типа заказа | ID_STRING |
| `OrderWaiter.Id` | ID официанта заказа | ID_STRING |
| `OrderWaiter.Name` | Официант заказа | STRING |
| `OriginName` | Источник заказа | STRING |
| `PayTypes` | Тип оплаты | STRING |
| `PayTypes.Combo` | Тип оплаты (комб.) | STRING |
| `PayTypes.GUID` | ID типа оплаты | ID_STRING |
| `PayTypes.Group` | Группа оплаты | ENUM |
| `PayTypes.IsPrintCheque` | Фиск. тип оплаты | ENUM |
| `PayTypes.VoucherNum` | Количество ваучеров | INTEGER |
| `PayableAmountInt` | Количество платных блюд | AMOUNT |
| `PaymentTransaction.Id` | ID проводки оплаты | STRING |
| `PaymentTransaction.Ids` | ID проводок оплат (комб.) | STRING |
| `PercentOfSummary.ByCol` | % по столбцу | PERCENT |
| `PercentOfSummary.ByRow` | % по строке | PERCENT |
| `PrechequeTime` | Время пречека | DATETIME |
| `PriceCategory` | Ценовая категория клиента | STRING |
| `PriceCategoryCard` | ЦК номер карты | STRING |
| `PriceCategoryDiscountCardOwner` | ЦК владелец карты | STRING |
| `PriceCategoryUserCardOwner` | ЦК контрагент | STRING |
| `ProductCostBase.MarkUp` | Наценка(%) | PERCENT |
| `ProductCostBase.OneItem` | Себестоимость единицы | MONEY |
| `ProductCostBase.Percent` | Себестоимость(%) | PERCENT |
| `ProductCostBase.PercentWithoutVAT` | Себестоимость без НДС(%) | PERCENT |
| `ProductCostBase.ProductCost` | Себестоимость | MONEY |
| `ProductCostBase.Profit` | Наценка | MONEY |
| `PublicExternalData` | Публичные данные плагинов | STRING |
| `PublicExternalData.Xml` | Публичные данные плагинов (XML) | STRING |
| `QuarterOpen` | Квартал | STRING |
| `RemovalType` | Причина удаления блюда | STRING |
| `RestaurantSection` | Отделение | STRING |
| `RestaurantSection.Id` | ID отделения | ID_STRING |
| `RestorauntGroup` | Группа | STRING |
| `RestorauntGroup.Id` | ID группы | ID |
| `SessionID` | ID кассовой смены | ID |
| `SessionNum` | Номер смены | INTEGER |
| `SoldWithDish` | Продано с блюдом | STRING |
| `SoldWithDish.Id` | ID основного блюда | ID_STRING |
| `SoldWithItem.Id` | ID позиции заказа основного блюда | ID |
| `SourceOrderId` | ID заказа-источника | ID |
| `SourceOrderNum` | Номер чека-источника | INTEGER |
| `Store.Id` | ID склада | ID_STRING |
| `Store.Name` | Со склада | STRING |
| `StoreTo` | На склад | STRING |
| `Storned` | Возврат чека | ENUM |
| `TableNum` | Номер стола | INTEGER |
| `UniqOrderId` | Чеков | INTEGER |
| `UniqOrderId.Id` | ID заказа | ID |
| `UniqOrderId.OrdersCount` | Заказов | AMOUNT |
| `VAT.Percent` | НДС(%) | PERCENT |
| `VAT.SplitVat` | НДС платит гость | ENUM |
| `VAT.Sum` | НДС по чекам(Сумма) | MONEY |
| `VatInvoice.DeletedInvoiceNumbers` | Номера удаленных счетов-фактур | STRING |
| `VatInvoice.InvoiceNumbers` | Номера счетов-фактур | STRING |
| `WaiterName` | Официант блюда | STRING |
| `WaiterName.ID` | ID официанта блюда | ID_STRING |
| `WaiterTeam.Id` | ID бригады официантов | ID_STRING |
| `WaiterTeam.Name` | Бригада официантов | STRING |
| `WeekInMonthOpen` | Неделя месяца | STRING |
| `WeekInYearOpen` | Неделя года | STRING |
| `WriteoffReason` | Причина списания | STRING |
| `WriteoffUser` | Списано на сотрудника | STRING |
| `YearOpen` | Год | STRING |
| `discountWithoutVAT` | Сумма скидки без НДС не включенного в стоимость | MONEY |
| `fullSum` | Сумма без НДС не включенного в стоимость | MONEY |
| `sumAfterDiscountWithoutVAT` | Сумма со скидкой без НДС не включенного в стоимость | MONEY |

</details>

## OLAP · DELIVERIES
всего полей: **285**

### похоже на автора — 12 шт.
| поле | название | тип | агрегируемое |
|---|---|---|---|
| `AuthUser.Id` | ID авторизовавшего | ID_STRING | False |
| `DishTags.IdsCombo` | ID пользовательских свойств (комб.) | STRING | False |
| `DishTag.Id` | ID пользовательского свойства | ID | False |
| `AuthUser` | Авторизовал | STRING | False |
| `CreditUser` | В кредит на... | STRING | False |
| `Delivery.CustomerCreatedDateTyped` | Дата создания клиента | DATE | False |
| `Card` | Карта авторизации | STRING | False |
| `CreditUser.Company` | Компания-контрагент | STRING | False |
| `DishTags.NamesCombo` | Пользовательские свойства (комб.) | STRING | False |
| `DishTag.Name` | Пользовательское свойство | STRING | False |
| `WriteoffUser` | Списано на сотрудника | STRING | False |
| `PriceCategoryUserCardOwner` | ЦК контрагент | STRING | False |

<details><summary>все поля</summary>

| поле | название | тип |
|---|---|---|
| `AuthUser` | Авторизовал | STRING |
| `AuthUser.Id` | ID авторизовавшего | ID_STRING |
| `Banquet` | Банкет | ENUM |
| `Bonus.CardNumber` | Номер бонусной карты | STRING |
| `Bonus.Sum` | Сумма бонуса | MONEY |
| `Bonus.Type` | Тип бонуса | STRING |
| `Card` | Карта авторизации | STRING |
| `CardNumber` | Номер карты оплаты | STRING |
| `CardOwner` | Владелец карты гостя | STRING |
| `CardType` | Кредитная карта | STRING |
| `CardTypeName` | Тип карты | STRING |
| `CashLocation` | Расположение кассы | STRING |
| `CashRegisterName` | Касса | STRING |
| `CashRegisterName.CashRegisterSerialNumber` | Серийный номер ФР | STRING |
| `CashRegisterName.Number` | Номер кассы | INTEGER |
| `Cashier` | Кассир | STRING |
| `Cashier.Code` | Табельный номер кассира | STRING |
| `Cashier.Id` | ID кассира | ID_STRING |
| `CloseTime` | Время закрытия | DATETIME |
| `CloseTime.Minutes15` | 15-минутный интервал закрытия | STRING |
| `Comment` | Комментарий к блюду | STRING |
| `Conception` | Концепция | STRING |
| `Conception.Code` | Код концепции | STRING |
| `Cooking.Cooking1Duration.Avg` | Продолжительность приготовления 1 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking2Duration.Avg` | Продолжительность приготовления 2 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking3Duration.Avg` | Продолжительность приготовления 3 (средняя) | DURATION_IN_SECONDS |
| `Cooking.Cooking4Duration.Avg` | Продолжительность приготовления 4 (средняя) | DURATION_IN_SECONDS |
| `Cooking.CookingDuration.Avg` | Продолжительность приготовления (средняя) | DURATION_IN_SECONDS |
| `Cooking.CookingLateTime.Avg` | Опоздание приготовления (средняя) | DURATION_IN_SECONDS |
| `Cooking.FeedLateTime.Avg` | Опоздание подачи (средняя) | DURATION_IN_SECONDS |
| `Cooking.GuestWaitTime.Avg` | Продолжительность ожидания гостя (средняя) | DURATION_IN_SECONDS |
| `Cooking.KitchenTime.Avg` | Продолжительность работы кухни (средняя) | DURATION_IN_SECONDS |
| `Cooking.PublicExternalData` | Публичные данные плагинов о приготовлении | STRING |
| `Cooking.PublicExternalData.Xml` | Публичные данные плагинов о приготовлении (XML) | STRING |
| `Cooking.ServeNumber` | Номер подачи | STRING |
| `Cooking.ServeTime.Avg` | Продолжительность подачи гостю (средняя) | DURATION_IN_SECONDS |
| `Cooking.StartDelayTime.Avg` | Задержка начала приготовления (средняя) | DURATION_IN_SECONDS |
| `CookingPlace` | Место приготовления | STRING |
| `CookingPlace.Id` | ID места приготовления | ID_STRING |
| `CookingPlaceType` | Тип места приготовления | STRING |
| `Counteragent.Name` | Контрагент | STRING |
| `CouponInfo.Number` | Номер купона | STRING |
| `CouponInfo.Series` | Серия купона | STRING |
| `CouponInfos` | Серии и номера купонов | STRING |
| `CreditUser` | В кредит на... | STRING |
| `CreditUser.Company` | Компания-контрагент | STRING |
| `Currencies.Currency` | Валюта оплаты | STRING |
| `Currencies.CurrencyRate` | Курс валюты оплаты | MONEY |
| `Currencies.SumInCurrency` | Сумма в валюте оплаты / заказ | OBJECT |
| `DayOfWeekOpen` | День недели | STRING |
| `DeletedWithWriteoff` | Блюдо удалено | ENUM |
| `DeletionComment` | Комментарий к удалению блюда | STRING |
| `Delivery.ActualTime` | Фактическое время доставки | DATETIME |
| `Delivery.Address` | Адрес | STRING |
| `Delivery.AggregatedAvgCourierMark` | Средняя оценка курьера, % | AMOUNT |
| `Delivery.AggregatedAvgFoodMark` | Средняя оценка кухни, % | AMOUNT |
| `Delivery.AggregatedAvgMark` | Средняя оценка доставки, % | AMOUNT |
| `Delivery.AggregatedAvgOperatorMark` | Средняя оценка оператора, % | AMOUNT |
| `Delivery.AvgCourierMark` | Оценка курьера, % | AMOUNT |
| `Delivery.AvgFoodMark` | Оценка кухни, % | AMOUNT |
| `Delivery.AvgMark` | Оценка доставки, % | AMOUNT |
| `Delivery.AvgOperatorMark` | Оценка оператора, % | AMOUNT |
| `Delivery.BillTime` | Время печати накладной | DATETIME |
| `Delivery.CancelCause` | Причина отмены доставки | STRING |
| `Delivery.CancelComment` | Комментарий к отмене доставки | STRING |
| `Delivery.City` | Город | STRING |
| `Delivery.CloseTime` | Время закрытия доставки | DATETIME |
| `Delivery.ConfirmTime` | Время подтверждения доставки | DATETIME |
| `Delivery.CookingFinishTime` | Время окончания приготовления | DATETIME |
| `Delivery.CookingToSendDuration` | Длит: посл.серв.печать-отправка | INTEGER |
| `Delivery.Courier` | Курьер | STRING |
| `Delivery.Courier.Id` | ID курьера | STRING |
| `Delivery.CustomerCardNumber` | Номер карты клиента | STRING |
| `Delivery.CustomerCardType` | Тип карты клиента | STRING |
| `Delivery.CustomerComment` | Комментарий к клиенту | STRING |
| `Delivery.CustomerCreatedDateTyped` | Дата создания клиента | DATE |
| `Delivery.CustomerMarketingSource` | Реклама клиента | STRING |
| `Delivery.CustomerName` | ФИО клиента | STRING |
| `Delivery.CustomerOpinionComment` | Отзыв клиента | STRING |
| `Delivery.CustomerPhone` | Телефон клиента | STRING |
| `Delivery.Delay` | Опоздание доставки(мин) | INTEGER |
| `Delivery.DelayAvg` | Ср.опоздание доставки(мин) | AMOUNT |
| `Delivery.DeliveryComment` | Комментарий к доставке | STRING |
| `Delivery.DeliveryOperator` | Оператор доставки | STRING |
| `Delivery.DeliveryOperator.Id` | ID оператора доставки | STRING |
| `Delivery.DiffBetweenActualDeliveryTimeAndPredictedDeliveryTime` | Отклонение от сроков доставки, фактическое от прогнозируемог | INTEGER |
| `Delivery.EcsService` | Курьерская служба | STRING |
| `Delivery.Email` | e-mail доставки | STRING |
| `Delivery.ExpectedTime` | Планируемое время доставки | DATETIME |
| `Delivery.ExternalCartographyId` | Идентификатор адреса | STRING |
| `Delivery.Id` | ID доставки | ID |
| `Delivery.Index` | Индекс адреса | STRING |
| `Delivery.IsAsap` | Как можно скорее | ENUM |
| `Delivery.IsDelivery` | Доставка | ENUM |
| `Delivery.Line1` | Куда везти | STRING |
| `Delivery.Line2` | Детали адреса | STRING |
| `Delivery.MarketingSource` | Реклама | STRING |
| `Delivery.Number` | Номер доставки | INTEGER |
| `Delivery.PackedTime` | Время окончания сборки доставки | DATETIME |
| `Delivery.Phone` | Телефон доставки | STRING |
| `Delivery.PredictedCookingCompleteTime` | Прогнозируемое время окончания готовки заказа | DATETIME |
| `Delivery.PredictedDeliveryTime` | Прогнозируемое время доставки | DATETIME |
| `Delivery.PrintTime` | Время печати доставки | DATETIME |
| `Delivery.Region` | Район | STRING |
| `Delivery.SendTime` | Время отправки доставки | DATETIME |
| `Delivery.ServiceType` | Тип доставки | ENUM |
| `Delivery.SourceKey` | Источник доставки | STRING |
| `Delivery.Street` | Улица | STRING |
| `Delivery.WayDuration` | Время в пути(мин) | INTEGER |
| `Delivery.WayDurationAvg` | Ср.время в пути(мин) | AMOUNT |
| `Delivery.WayDurationSum` | Сумм.время в пути(мин) | INTEGER |
| `Delivery.Zone` | Зона доставки | STRING |
| `Department` | Торговое предприятие | STRING |
| `Department.Category1` | Категория 1 | STRING |
| `Department.Category2` | Категория 2 | STRING |
| `Department.Category3` | Категория 3 | STRING |
| `Department.Category4` | Категория 4 | STRING |
| `Department.Category5` | Категория 5 | STRING |
| `Department.Code` | Код подразделения | STRING |
| `Department.Id` | ID подразделения | ID_STRING |
| `DiscountPercent` | Процент скидки | PERCENT |
| `DiscountSum` | Сумма скидки | MONEY |
| `DishAmountInt` | Количество блюд | AMOUNT |
| `DishAmountInt.PerOrder` | Ср. количество блюд на чек | AMOUNT |
| `DishCategory` | Категория блюда | STRING |
| `DishCategory.Accounting` | Бухгалтерская категория блюда | STRING |
| `DishCategory.Accounting.Id` | ID бухгалтерской категории блюда | ID |
| `DishCategory.Id` | ID категории блюда | ID_STRING |
| `DishCode` | Код блюда | STRING |
| `DishCode.Quick` | Код быстрого набора блюда | STRING |
| `DishDiscountSumInt` | Сумма со скидкой | MONEY |
| `DishDiscountSumInt.average` | Средняя сумма заказа | MONEY |
| `DishDiscountSumInt.averageByGuest` | Средняя выручка с гостя | MONEY |
| `DishDiscountSumInt.averagePrice` | Средняя цена без НДС | MONEY |
| `DishDiscountSumInt.averagePriceWithVAT` | Средняя цена | MONEY |
| `DishDiscountSumInt.averageWithoutVAT` | Средняя сумма заказа без НДС | MONEY |
| `DishDiscountSumInt.withoutVAT` | Сумма со скидкой без НДС | MONEY |
| `DishForeignName` | Наименование блюда на иностранном языке | STRING |
| `DishFullName` | Полное наименование блюда | STRING |
| `DishGroup` | Группа блюда | STRING |
| `DishGroup.Hierarchy` | Иерархия блюда | STRING |
| `DishGroup.Id` | ID группы блюда | ID |
| `DishGroup.Num` | Код группы блюда | STRING |
| `DishGroup.SecondParent` | Группа блюда 2-го уровня | STRING |
| `DishGroup.ThirdParent` | Группа блюда 3-го уровня | STRING |
| `DishGroup.TopParent` | Группа блюда 1-го уровня | STRING |
| `DishId` | ID блюда | ID_STRING |
| `DishMeasureUnit` | Единица измерения | STRING |
| `DishName` | Блюдо | STRING |
| `DishReturnSum` | Сумма возврата | MONEY |
| `DishReturnSum.withoutVAT` | Сумма возврата без НДС | MONEY |
| `DishServicePrintTime` | Сервисная печать блюда | DATETIME |
| `DishServicePrintTime.Max` | Сервисная печать последнего блюда | DATETIME |
| `DishServicePrintTime.OpenToLastPrintDuration` | Длит: откр.-посл.серв.печать | INTEGER |
| `DishSize.Id` | ID размера блюда | ID_STRING |
| `DishSize.Name` | Размер блюда | STRING |
| `DishSize.Priority` | Порядковый номер размера блюда | INTEGER |
| `DishSize.Scale.Id` | ID шкалы размеров блюда | ID |
| `DishSize.Scale.Name` | Шкала размеров блюда | STRING |
| `DishSize.ShortName` | Код размера блюда | STRING |
| `DishSumInt` | Сумма без скидки | MONEY |
| `DishSumInt.averagePriceWithVAT` | Средняя цена без скидки | MONEY |
| `DishTag.Id` | ID пользовательского свойства | ID |
| `DishTag.Name` | Пользовательское свойство | STRING |
| `DishTags.IdsCombo` | ID пользовательских свойств (комб.) | STRING |
| `DishTags.NamesCombo` | Пользовательские свойства (комб.) | STRING |
| `DishTaxCategory.Id` | ID налоговой категории | ID |
| `DishTaxCategory.Name` | Налоговая категория | STRING |
| `DishType` | Тип товара | ENUM |
| `ExternalNumber` | Внешний номер заказа | STRING |
| `FiscalChequeNumber` | Номера фиск. чеков | STRING |
| `GroupOrderId` | ID группового заказа | ID |
| `GroupOrderNum` | Номер группового чека | INTEGER |
| `GuestNum` | Количество гостей | AMOUNT |
| `GuestNum.Avg` | Ср.кол-во гостей на чек | AMOUNT |
| `HourClose` | Час закрытия | STRING |
| `HourOpen` | Час открытия | STRING |
| `IncentiveSumBase.Sum` | Мотивационный бонус | MONEY |
| `IncreasePercent` | Процент надбавки | PERCENT |
| `IncreaseSum` | Сумма надбавки | MONEY |
| `ItemSaleEvent.Id` | ID позиции заказа | ID |
| `ItemSaleEventDiscountType` | Наименование скидки, надбавки | STRING |
| `ItemSaleEventDiscountType.ComboAmount` | Количество Комбо | INTEGER |
| `ItemSaleEventDiscountType.ComboGroupId` | ID Шага Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboGroupName` | Шаг Комбо | STRING |
| `ItemSaleEventDiscountType.ComboId` | ID Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboName` | Название Комбо | STRING |
| `ItemSaleEventDiscountType.ComboSizeId` | ID размера Комбо | ID_STRING |
| `ItemSaleEventDiscountType.ComboSizeName` | Размер Комбо | STRING |
| `ItemSaleEventDiscountType.DiscountAmount` | Колич. блюд со скидкой | AMOUNT |
| `JurName` | Юридическое лицо | STRING |
| `LocalTax1.Sum` | Местный налог 1 | MONEY |
| `LocalTax2.Sum` | Местный налог 2 | MONEY |
| `LocalTax3.Sum` | Местный налог 3 | MONEY |
| `LocalTax4.Sum` | Местный налог 4 | MONEY |
| `LocalTax5.Sum` | Местный налог 5 | MONEY |
| `Mounth` | Месяц | STRING |
| `NonCashPaymentType` | Безналичный тип оплаты | STRING |
| `NonCashPaymentType.DocumentType` | Тип документа списания | ENUM |
| `OpenDate.Typed` | Учетный день | DATE |
| `OpenTime` | Время открытия | DATETIME |
| `OpenTime.Minutes15` | 15-минутный интервал открытия | STRING |
| `OperationType` | Операция | ENUM |
| `OrderComment` | Комментарий заказа | STRING |
| `OrderDeleted` | Заказ удален | ENUM |
| `OrderDiscount.GuestCard` | Гостевая карта | STRING |
| `OrderDiscount.Type` | Тип скидки | STRING |
| `OrderDiscount.Type.IDs` | ID типов скидок | STRING |
| `OrderIncrease.Type` | Тип надбавки | STRING |
| `OrderIncrease.Type.IDs` | ID типов надбавок | STRING |
| `OrderItems` | Позиций чека | INTEGER |
| `OrderNum` | Номер чека | INTEGER |
| `OrderServiceType` | Режим обслуживания | ENUM |
| `OrderTime.AverageOrderTime` | Ср.время обсл.(мин) | AMOUNT |
| `OrderTime.AveragePrechequeTime` | Ср.время в пречеке (мин) | AMOUNT |
| `OrderTime.OrderLength` | Время обслуживания (мин) | INTEGER |
| `OrderTime.OrderLengthSum` | Время обсл.сумм.(мин) | INTEGER |
| `OrderTime.PrechequeLength` | Время в пречеке (мин) | INTEGER |
| `OrderType` | Тип заказа | STRING |
| `OrderType.Id` | ID типа заказа | ID_STRING |
| `OrderWaiter.Id` | ID официанта заказа | ID_STRING |
| `OrderWaiter.Name` | Официант заказа | STRING |
| `OriginName` | Источник заказа | STRING |
| `PayTypes` | Тип оплаты | STRING |
| `PayTypes.Combo` | Тип оплаты (комб.) | STRING |
| `PayTypes.GUID` | ID типа оплаты | ID_STRING |
| `PayTypes.Group` | Группа оплаты | ENUM |
| `PayTypes.IsPrintCheque` | Фиск. тип оплаты | ENUM |
| `PayTypes.VoucherNum` | Количество ваучеров | INTEGER |
| `PayableAmountInt` | Количество платных блюд | AMOUNT |
| `PaymentTransaction.Id` | ID проводки оплаты | STRING |
| `PaymentTransaction.Ids` | ID проводок оплат (комб.) | STRING |
| `PercentOfSummary.ByCol` | % по столбцу | PERCENT |
| `PercentOfSummary.ByRow` | % по строке | PERCENT |
| `PrechequeTime` | Время пречека | DATETIME |
| `PriceCategory` | Ценовая категория клиента | STRING |
| `PriceCategoryCard` | ЦК номер карты | STRING |
| `PriceCategoryDiscountCardOwner` | ЦК владелец карты | STRING |
| `PriceCategoryUserCardOwner` | ЦК контрагент | STRING |
| `ProductCostBase.MarkUp` | Наценка(%) | PERCENT |
| `ProductCostBase.OneItem` | Себестоимость единицы | MONEY |
| `ProductCostBase.Percent` | Себестоимость(%) | PERCENT |
| `ProductCostBase.PercentWithoutVAT` | Себестоимость без НДС(%) | PERCENT |
| `ProductCostBase.ProductCost` | Себестоимость | MONEY |
| `ProductCostBase.Profit` | Наценка | MONEY |
| `PublicExternalData` | Публичные данные плагинов | STRING |
| `PublicExternalData.Xml` | Публичные данные плагинов (XML) | STRING |
| `QuarterOpen` | Квартал | STRING |
| `RemovalType` | Причина удаления блюда | STRING |
| `RestaurantSection` | Отделение | STRING |
| `RestaurantSection.Id` | ID отделения | ID_STRING |
| `RestorauntGroup` | Группа | STRING |
| `RestorauntGroup.Id` | ID группы | ID |
| `SessionID` | ID кассовой смены | ID |
| `SessionNum` | Номер смены | INTEGER |
| `SoldWithDish` | Продано с блюдом | STRING |
| `SoldWithDish.Id` | ID основного блюда | ID_STRING |
| `SoldWithItem.Id` | ID позиции заказа основного блюда | ID |
| `SourceOrderId` | ID заказа-источника | ID |
| `SourceOrderNum` | Номер чека-источника | INTEGER |
| `Store.Id` | ID склада | ID_STRING |
| `Store.Name` | Со склада | STRING |
| `StoreTo` | На склад | STRING |
| `Storned` | Возврат чека | ENUM |
| `TableNum` | Номер стола | INTEGER |
| `UniqOrderId` | Чеков | INTEGER |
| `UniqOrderId.Id` | ID заказа | ID |
| `UniqOrderId.OrdersCount` | Заказов | AMOUNT |
| `VAT.Percent` | НДС(%) | PERCENT |
| `VAT.SplitVat` | НДС платит гость | ENUM |
| `VAT.Sum` | НДС по чекам(Сумма) | MONEY |
| `VatInvoice.DeletedInvoiceNumbers` | Номера удаленных счетов-фактур | STRING |
| `VatInvoice.InvoiceNumbers` | Номера счетов-фактур | STRING |
| `WaiterName` | Официант блюда | STRING |
| `WaiterName.ID` | ID официанта блюда | ID_STRING |
| `WaiterTeam.Id` | ID бригады официантов | ID_STRING |
| `WaiterTeam.Name` | Бригада официантов | STRING |
| `WeekInMonthOpen` | Неделя месяца | STRING |
| `WeekInYearOpen` | Неделя года | STRING |
| `WriteoffReason` | Причина списания | STRING |
| `WriteoffUser` | Списано на сотрудника | STRING |
| `YearOpen` | Год | STRING |
| `discountWithoutVAT` | Сумма скидки без НДС не включенного в стоимость | MONEY |
| `fullSum` | Сумма без НДС не включенного в стоимость | MONEY |
| `sumAfterDiscountWithoutVAT` | Сумма со скидкой без НДС не включенного в стоимость | MONEY |

</details>

## Журнал событий 2026-09-22 — 2026-10-07
событий: **223**, сотрудников в справочнике: **8622**

| тип события | сколько | есть пользователь |
|---|---|---|
| `dataReplicationResult` | 125 | да (125) |
| `documentModified` | 25 | да (25) |
| `customersExchangeEvent` | 24 | да (24) |
| `productUpdated` | 19 | да (19) |
| `nomenclatureExportEvent` | 12 | да (12) |
| `documentCreated` | 9 | да (9) |
| `backLogin` | 7 | да (7) |
| `pinAuthorization` | 1 | да (1) |
| `backLogout` | 1 | да (1) |

## примеры документных и денежных событий
### `documentCreated` · 2026-10-06T07:13:50.737+05:00 · пользователь: **Аман Бану**
| поле | значение | тип |
|---|---|---|
| user | Аман Бану | User |
| documentType | PRODUCTION_DOCUMENT | java.lang.String |
| documentId | 4de12eca-35f3-4dcc-8430-9f5de4afacaa | resto.db.Guid |
| terminal | 178d87e7-0c7a-7af7-0198-3c92e36178ae | Terminal |
| documentNumber | 7654 | java.lang.String |

### `documentModified` · 2026-10-06T09:06:26.970+05:00 · пользователь: **Азимова Саням**
| поле | значение | тип |
|---|---|---|
| documentType | INTERNAL_TRANSFER | java.lang.String |
| documentId | 18ce4917-e2e6-4fa1-af2f-c67878451769 | resto.db.Guid |
| user | Азимова Саням | User |
| documentNumber | 5679 | java.lang.String |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |

### `documentCreated` · 2026-10-06T09:21:59.043+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| documentType | TRANSFORMATION_DOCUMENT | java.lang.String |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |
| documentNumber | 0986 | java.lang.String |
| documentId | 3144dd09-b97b-837a-01a1-0e16ddc7b132 | resto.db.Guid |
| user | Нурлан Лаззат У | User |

### `documentModified` · 2026-10-06T09:22:12.477+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |
| documentId | 3144dd09-b97b-837a-01a1-0e16ddc7b132 | resto.db.Guid |
| documentType | TRANSFORMATION_DOCUMENT | java.lang.String |
| documentNumber | 0986 | java.lang.String |
| user | Нурлан Лаззат У | User |

### `documentModified` · 2026-10-06T09:24:27.400+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| user | Нурлан Лаззат У | User |
| documentNumber | 7646 | java.lang.String |
| documentType | PRODUCTION_DOCUMENT | java.lang.String |
| documentId | 3b928105-60c1-4914-ae02-493ab068639a | resto.db.Guid |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |

### `documentModified` · 2026-10-06T09:25:14.463+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| documentNumber | 0078 | java.lang.String |
| documentId | c60f7bc9-b825-4023-850c-494118122c70 | resto.db.Guid |
| documentType | INCOMING_INVENTORY | java.lang.String |
| user | Нурлан Лаззат У | User |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |

### `documentCreated` · 2026-10-06T09:25:40.693+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| documentId | cbf42a5a-7e24-4adc-a811-2f840d062e6d | resto.db.Guid |
| documentType | PRODUCTION_DOCUMENT | java.lang.String |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |
| documentNumber | 7655 | java.lang.String |
| user | Нурлан Лаззат У | User |

### `documentCreated` · 2026-10-06T09:43:29.427+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |
| documentId | b0ab20c9-93b3-4931-bb61-c2321f3fb17f | resto.db.Guid |
| documentNumber | 7656 | java.lang.String |
| documentType | PRODUCTION_DOCUMENT | java.lang.String |
| user | Нурлан Лаззат У | User |

### `documentModified` · 2026-10-06T09:43:33.677+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| documentId | 20c68984-b601-4e3c-ba91-5dc2bcda34df | resto.db.Guid |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |
| user | Нурлан Лаззат У | User |
| documentType | PRODUCTION_DOCUMENT | java.lang.String |
| documentNumber | 7645 | java.lang.String |

### `documentModified` · 2026-10-06T09:44:20.493+05:00 · пользователь: **Нурлан Лаззат У**
| поле | значение | тип |
|---|---|---|
| user | Нурлан Лаззат У | User |
| documentType | INCOMING_INVENTORY | java.lang.String |
| documentId | c60f7bc9-b825-4023-850c-494118122c70 | resto.db.Guid |
| documentNumber | 0078 | java.lang.String |
| terminal | b37fc400-1956-b1c6-017c-aefa67b1727f | Terminal |

