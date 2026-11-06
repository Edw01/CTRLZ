unit main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls,
  ComCtrls, Buttons, TAGraph, TASeries, TATypes, LazSerial, fphttpclient, fpjson,
  jsonparser, opensslsockets;

type

  { TMyForm }

  TMyForm = class(TForm)
    ChartAmbiental: TChart;
    ChartHistograma: TChart;
    Serie1: TLineSeries;
    Serie2: TLineSeries;
    Serie3: TLineSeries;
    Bar1: TBarSeries;
    MySer: TLazSerial;
    CB_COM: TCheckBox;
    CB1: TCheckBox;
    GB_Sensores: TGroupBox;
    PanelTempHeader: TPanel;
    PanelTempVal: TPanel;
    PanelHrHeader: TPanel;
    PanelHrVal: TPanel;
    PanelUMA: TPanel;
    PanelMP: TPanel;
    LblUgM3: TLabel;
    LblSizes: TLabel;
    Te: TLabel;
    Hr: TLabel;
    RB_UMA1: TRadioButton;
    RB_UMA2: TRadioButton;
    RB_UMA3: TRadioButton;
    RB_UMA4: TRadioButton;
    RB_UMA5: TRadioButton;
    RB_MP01: TRadioButton;
    RB_MP25: TRadioButton;
    RB_MP10: TRadioButton;
    SB1: TStatusBar;
    Timer1: TTimer;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var CloseAction: TCloseAction);
    procedure CB_COMChange(Sender: TObject);
    procedure MySerRxData(Sender: TObject);
    procedure RB_UMAChange(Sender: TObject);
    procedure RB_MPChange(Sender: TObject);
    procedure Timer1Timer(Sender: TObject);
    procedure Clear_Trama;
    procedure Send_Data_To_Flask(aAux: Array of Integer);
  private

  public

  end;

Var
  MyForm: TMyForm;
  aMP01 : Array[0..11] of Integer;
  aMP25 : Array[0..11] of Integer;
  aMP10 : Array[0..11] of Integer;
  aHisto: Array[0..05] of Integer;
  aClr  : Array[0..5]  of TColor;
  nID   : Byte;
  lFlask: Boolean;

implementation

{$R *.lfm}

{ TMyForm }

Procedure TMyForm.FormCreate(Sender: TObject);
Begin
  // Colores para las 6 barras del Histograma (0.3, 0.5, 1.0, 2.5, 5.0 y 10 um)
  aClr[0] := clRed;
  aClr[1] := clGreen;
  aClr[2] := clBlue;
  aClr[3] := clYellow;
  aClr[4] := clLime;
  aClr[5] := $00F5D4B8; // Celeste claro

  nID := 1;
  lFlask := False;

  SB1.Panels[0].Text := 'Fecha : ' + FormatDateTime('dd-mm-yyyy', Now) +
                        ' - Hora : ' + FormatDateTime('h:nn:ss', Now);
  SB1.Panels[1].Text := 'Data : ';

  Clear_Trama;
End;

Procedure TMyForm.FormClose(Sender: TObject; var CloseAction: TCloseAction);
Begin
  If MySer.Active Then
    MySer.Active := False;
End;

Procedure TMyForm.Clear_Trama;
Var
  nPos: Integer;
Begin
  Serie1.Clear;
  Serie2.Clear;
  Serie3.Clear;
  Bar1.Clear;

  For nPos := 0 To 11 Do
  Begin
    aMP01[nPos] := 0; aMP25[nPos] := 0; aMP10[nPos] := 0;
    Serie1.AddXY(nPos, aMP01[nPos]);
    Serie2.AddXY(nPos, aMP25[nPos]);
    Serie3.AddXY(nPos, aMP10[nPos]);
  End;

  For nPos := 0 To 5 Do
  Begin
    aHisto[nPos] := 0;
    Bar1.AddXY(nPos, aHisto[nPos], '', aClr[nPos]);
  End;
End;

Procedure TMyForm.CB_COMChange(Sender: TObject);
Begin
  Try
    MySer.Active := CB_COM.Checked;
  Except
    On E: Exception Do
    Begin
      ShowMessage('No se pudo abrir el puerto ' + MySer.Device + ': ' + E.Message);
      CB_COM.Checked := False;
    End;
  End;
End;

Procedure TMyForm.RB_UMAChange(Sender: TObject);
Begin
  If RB_UMA1.Checked Then nID := 1
  Else If RB_UMA2.Checked Then nID := 2
  Else If RB_UMA3.Checked Then nID := 3
  Else If RB_UMA4.Checked Then nID := 4
  Else If RB_UMA5.Checked Then nID := 5;

  Clear_Trama;
End;

Procedure TMyForm.RB_MPChange(Sender: TObject);
Begin
  Serie1.Marks.Visible := RB_MP01.Checked;
  Serie2.Marks.Visible := RB_MP25.Checked;
  Serie3.Marks.Visible := RB_MP10.Checked;
End;

Procedure TMyForm.Timer1Timer(Sender: TObject);
Begin
  SB1.Panels[0].Text := 'Fecha : ' + FormatDateTime('dd-mm-yyyy', Now) +
                        ' - Hora : ' + FormatDateTime('h:nn:ss', Now);
End;

Procedure TMyForm.Send_Data_To_Flask(aAux: Array of Integer);
Var
  Data  : TJSONObject;
  sResp : String;
Begin
  Data := TJSONObject.Create();
  Try
    Data.Add('id', aAux[0]);   // ID EMA
    Data.Add('mp01', aAux[1]); // MP 1.0 ug/m3
    Data.Add('mp02', aAux[2]); // MP 2.5 ug/m3
    Data.Add('mp03', aAux[3]); // MP 10 ug/m3
    // Histograma Particulas
    Data.Add('hi01', aAux[4]); // MP 0.3 um
    Data.Add('hi02', aAux[5]); // MP 0.5 um
    Data.Add('hi03', aAux[6]); // MP 1.0 um
    Data.Add('hi04', aAux[7]); // MP 2.5 um
    Data.Add('hi05', aAux[8]); // MP 5.0 um
    Data.Add('hi06', aAux[9]); // MP 10 um
    // Data Tempe + HR
    Data.Add('te', aAux[10]);  // Tempe
    Data.Add('hr', aAux[11]);  // Humedad Relativa

    With TFPHttpClient.Create(Nil) Do
    Try
      AddHeader('Content-Type', 'application/json');
      RequestBody := TStringStream.Create(Data.AsJSON);
      Try
        sResp := Post('http://127.0.0.1:7070/data');
      Except
        // Ignorar errores de red temporales para no detener la recepcion serial
      End;
    Finally
      RequestBody.Free;
      Free;
    End;
  Finally
    Data.Free;
  End;
End;

Procedure TMyForm.MySerRxData(Sender: TObject);
Var
  aAux  : Array[0..11] of Integer;
  sLine : String;
  sPaq  : String;
  nI, nPos : Byte;
Begin
  sLine := Trim(MySer.ReadData);
  If sLine = '' Then Exit;

  // Limpiar saltos de linea si vienen en la trama
  If Pos(#10, sLine) > 0 Then
    sLine := Trim(Copy(sLine, 1, Pos(#10, sLine) - 1));
  If Pos(#13, sLine) > 0 Then
    sLine := Trim(Copy(sLine, 1, Pos(#13, sLine) - 1));

  sPaq := sLine;

  Try
    For nI := 0 To 10 Do
    Begin
      nPos := Pos(',', sLine);
      If nPos = 0 Then Exit;
      aAux[nI] := StrToInt(Trim(Copy(sLine, 1, nPos - 1)));
      Delete(sLine, 1, nPos);
    End;
    aAux[11] := StrToInt(Trim(sLine));
  Except
    Exit;
  End;

  If aAux[0] = nID Then
  Begin
    // Enviamos a Flask Web Server
    If CB1.Checked Then Send_Data_To_Flask(aAux);
    SB1.Panels[1].Text := 'Data : ' + sPaq;

    // Graficamos Tempe y HR
    Te.Caption := IntToStr(aAux[10]);
    Hr.Caption := IntToStr(aAux[11]);

    // Limpiamos todas las series y barras
    Serie1.Clear; Serie2.Clear; Serie3.Clear; Bar1.Clear;

    // Graficos de Barras
    For nPos := 0 To 5 Do
    Begin
      aHisto[nPos] := aAux[nPos + 4];
      Bar1.AddXY(nPos, aHisto[nPos], '', aClr[nPos]);
    End;

    // Graficos de Series - aAux tiene todos los datos
    // Colocamos las Series recibidas en ultima posicion aMPXX
    aMP01[10] := aAux[1]; aMP25[10] := aAux[2]; aMP10[10] := aAux[3];
    For nPos := 0 To 10 Do
    Begin
      Serie1.AddXY(nPos, aMP01[nPos]);
      Serie2.AddXY(nPos, aMP25[nPos]);
      Serie3.AddXY(nPos, aMP10[nPos]);
      aMP01[nPos] := aMP01[nPos + 1]; // Scrolling Data Left..
      aMP25[nPos] := aMP25[nPos + 1];
      aMP10[nPos] := aMP10[nPos + 1];
    End;
  End;
End;

end.
